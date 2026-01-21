#!/usr/bin/env python3
import os
import time
import math
import ctypes
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List

import cv2
import numpy as np
import tensorrt as trt

from pose_sensor_fusion.vision.realsense_ai_api import RealSenseAIApi, FrameBundle, Intrinsics
from pose_sensor_fusion.vision.pose_filter import OneEuroFilter3D
from pose_sensor_fusion.vision.cuda_runtime import*


# =========================
# TRT wrapper
# =========================
TRT_LOGGER = trt.Logger(trt.Logger.INFO)

@dataclass
class TrtIO:
    input_name: str
    output_name: str
    input_shape: Tuple[int, int, int, int]   # NCHW
    output_shape: Tuple[int, int, int]       # (1,56,8400)
    input_dtype: np.dtype
    output_dtype: np.dtype

class TrtEngine:
    def __init__(self, engine_path: str):
        with open(engine_path, "rb") as f, trt.Runtime(TRT_LOGGER) as runtime:
            self.engine = runtime.deserialize_cuda_engine(f.read())
        if self.engine is None:
            raise RuntimeError("Failed to deserialize engine")

        self.context = self.engine.create_execution_context()
        if self.context is None:
            raise RuntimeError("Failed to create execution context")

        # assume fixed: input 1x3x640x640, output 1x56x8400
        self.input_name = self.engine.get_tensor_name(0)
        self.output_name = self.engine.get_tensor_name(1)

        in_shape = tuple(self.engine.get_tensor_shape(self.input_name))
        out_shape = tuple(self.engine.get_tensor_shape(self.output_name))

        self.input_shape = (in_shape[0], in_shape[1], in_shape[2], in_shape[3])
        self.output_shape = (out_shape[0], out_shape[1], out_shape[2])

        in_dtype = trt.nptype(self.engine.get_tensor_dtype(self.input_name))
        out_dtype = trt.nptype(self.engine.get_tensor_dtype(self.output_name))

        self.io = TrtIO(
            input_name=self.input_name,
            output_name=self.output_name,
            input_shape=self.input_shape,
            output_shape=self.output_shape,
            input_dtype=in_dtype,
            output_dtype=out_dtype,
        )

        self.stream = cudaStreamCreate()

        self.in_bytes = int(np.prod(self.input_shape) * np.dtype(self.io.input_dtype).itemsize)
        self.out_bytes = int(np.prod(self.output_shape) * np.dtype(self.io.output_dtype).itemsize)

        self.d_input = cudaMalloc(self.in_bytes)
        self.d_output = cudaMalloc(self.out_bytes)

        self.h_input = np.empty(self.input_shape, dtype=self.io.input_dtype)
        self.h_output = np.empty(self.output_shape, dtype=self.io.output_dtype)

        self.context.set_tensor_address(self.input_name, self.d_input)
        self.context.set_tensor_address(self.output_name, self.d_output)

    def infer(self, input_nchw: np.ndarray) -> np.ndarray:
        assert input_nchw.shape == self.input_shape, (input_nchw.shape, self.input_shape)
        if input_nchw.dtype != self.io.input_dtype:
            input_nchw = input_nchw.astype(self.io.input_dtype, copy=False)

        np.copyto(self.h_input, input_nchw)

        cudaMemcpyAsync(self.d_input, self.h_input.ctypes.data, self.in_bytes, cudaMemcpyHostToDevice, self.stream)

        ok = self.context.execute_async_v3(int(self.stream))
        if not ok:
            raise RuntimeError("execute_async_v3 failed")

        cudaMemcpyAsync(self.h_output.ctypes.data, self.d_output, self.out_bytes, cudaMemcpyDeviceToHost, self.stream)
        cudaStreamSynchronize(self.stream)

        return self.h_output.copy()

    def close(self):
        try:
            cudaFree(self.d_input)
            cudaFree(self.d_output)
        finally:
            cudaStreamDestroy(self.stream)

# =========================
# Depth robust sampling + deprojection (pinhole, no distortion)
# =========================
@dataclass
class DepthSample:
    z_m: Optional[float]
    xyz_m: Optional[np.ndarray]
    valid: bool
    debug: str = ""

def deproject_pixel_to_point_pinhole(intr: Intrinsics, u: int, v: int, z_m: float) -> np.ndarray:
    X = (float(u) - intr.ppx) / intr.fx * float(z_m)
    Y = (float(v) - intr.ppy) / intr.fy * float(z_m)
    Z = float(z_m)
    return np.array([X, Y, Z], dtype=np.float32)

def robust_depth_at(
    depth_z16: np.ndarray,
    depth_scale: float,
    intr: Intrinsics,
    u: int,
    v: int,
    roi: int = 5,
    min_valid_ratio: float = 0.25,
    outlier_mad_k: float = 3.5
) -> DepthSample:
    if depth_z16 is None:
        return DepthSample(None, None, False, "no depth frame")

    h, w = depth_z16.shape[:2]
    if u < 0 or v < 0 or u >= w or v >= h:
        return DepthSample(None, None, False, "OOB")

    x0 = max(u - roi, 0)
    x1 = min(u + roi + 1, w)
    y0 = max(v - roi, 0)
    y1 = min(v + roi + 1, h)

    patch = depth_z16[y0:y1, x0:x1].astype(np.float32)
    vals = patch.reshape(-1)
    vals = vals[vals > 0]

    if vals.size == 0:
        return DepthSample(None, None, False, "no depth")

    if (vals.size / patch.size) < min_valid_ratio:
        return DepthSample(None, None, False, "too few valid")

    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) + 1e-6
    zscore = np.abs(vals - med) / mad
    kept = vals[zscore < outlier_mad_k]

    if kept.size < max(3, int(vals.size * 0.2)):
        final = med
        dbg = "mad fallback"
    else:
        final = float(np.median(kept))
        dbg = "mad ok"

    z_m = final * depth_scale
    xyz = deproject_pixel_to_point_pinhole(intr, u, v, z_m)
    return DepthSample(z_m, xyz, True, dbg)


# =========================
# YOLO Pose postprocess (Ultralytics style)
# output: (1,56,8400)
#  0:4 bbox cxcywh on 640
#  4   obj conf
#  5:56 keypoints (17*3) x,y,score on 640
# =========================
def nms_xywh(boxes_xywh: np.ndarray, scores: np.ndarray, iou_th: float) -> np.ndarray:
    cx, cy, w, h = boxes_xywh[:, 0], boxes_xywh[:, 1], boxes_xywh[:, 2], boxes_xywh[:, 3]
    x1 = cx - w / 2
    y1 = cy - h / 2
    x2 = cx + w / 2
    y2 = cy + h / 2
    areas = (x2 - x1) * (y2 - y1)

    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        iw = np.maximum(0.0, xx2 - xx1)
        ih = np.maximum(0.0, yy2 - yy1)
        inter = iw * ih
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        inds = np.where(iou <= iou_th)[0]
        order = order[inds + 1]
    return np.array(keep, dtype=np.int32)

def decode_pose(output: np.ndarray, conf_th: float = 0.25, iou_th: float = 0.45):
    pred = output[0].transpose(1, 0)  # (8400,56)
    boxes = pred[:, 0:4]
    obj = pred[:, 4]
    kpts = pred[:, 5:].reshape(-1, 17, 3)

    m = obj >= conf_th
    boxes = boxes[m]
    obj = obj[m]
    kpts = kpts[m]

    if boxes.shape[0] == 0:
        return np.zeros((0, 4), np.float32), np.zeros((0,), np.float32), np.zeros((0, 17, 3), np.float32)

    keep = nms_xywh(boxes, obj, iou_th)
    return boxes[keep], obj[keep], kpts[keep]

def iou_xywh(a: np.ndarray, b: np.ndarray) -> float:
    ax1, ay1 = a[0] - a[2] / 2, a[1] - a[3] / 2
    ax2, ay2 = a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1 = b[0] - b[2] / 2, b[1] - b[3] / 2
    bx2, by2 = b[0] + b[2] / 2, b[1] + b[3] / 2

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
    inter = iw * ih
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter + 1e-9)

@dataclass
class TrackState:
    bbox: Optional[np.ndarray] = None
    kpts_640: Optional[np.ndarray] = None
    last_seen: float = 0.0

def pick_person(boxes: np.ndarray, scores: np.ndarray, kpts: np.ndarray, st: TrackState, stick_iou: float = 0.2):
    if boxes.shape[0] == 0:
        return None

    if st.bbox is None:
        i = int(scores.argmax())
        return boxes[i], float(scores[i]), kpts[i]

    ious = np.array([iou_xywh(st.bbox, b) for b in boxes], dtype=np.float32)
    best = int(ious.argmax())
    if float(ious[best]) >= stick_iou:
        return boxes[best], float(scores[best]), kpts[best]

    i = int(scores.argmax())
    return boxes[i], float(scores[i]), kpts[i]


# =========================
# Letterbox preprocess + unletterbox
# =========================
def preprocess_bgr_letterbox(frame_bgr: np.ndarray, size: int = 640):
    h, w = frame_bgr.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((size, size, 3), dtype=np.uint8)
    dx = (size - nw) // 2
    dy = (size - nh) // 2
    canvas[dy:dy + nh, dx:dx + nw] = resized

    x = canvas.astype(np.float32) / 255.0
    x = x.transpose(2, 0, 1)[None, ...]  # (1,3,640,640)
    return x, scale, dx, dy

def unletterbox_points(kpts_640: np.ndarray, scale: float, dx: int, dy: int) -> np.ndarray:
    out = kpts_640.copy()
    out[:, 0] = (out[:, 0] - dx) / (scale + 1e-9)
    out[:, 1] = (out[:, 1] - dy) / (scale + 1e-9)
    return out


# =========================
# Geometry, drawing
# =========================
COCO = {
    "NOSE": 0,
    "L_EYE": 1,
    "R_EYE": 2,
    "L_EAR": 3,
    "R_EAR": 4,
    "L_SHOULDER": 5,
    "R_SHOULDER": 6,
    "L_ELBOW": 7,
    "R_ELBOW": 8,
    "L_WRIST": 9,
    "R_WRIST": 10,
    "L_HIP": 11,
    "R_HIP": 12,
    "L_KNEE": 13,
    "R_KNEE": 14,
    "L_ANKLE": 15,
    "R_ANKLE": 16,
}

COCO_EDGES = [
    (5, 7), (7, 9),
    (6, 8), (8, 10),
    (5, 6),
    (5, 11), (6, 12),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (0, 1), (0, 2), (1, 3), (2, 4)
]

def draw_pose_2d(img: np.ndarray, kpts_xy: np.ndarray, kp_th: float = 0.25):
    for (x, y, s) in kpts_xy:
        if float(s) >= kp_th:
            cv2.circle(img, (int(x), int(y)), 3, (0, 255, 0), -1)
    for a, b in COCO_EDGES:
        xa, ya, sa = kpts_xy[a]
        xb, yb, sb = kpts_xy[b]
        if float(sa) >= kp_th and float(sb) >= kp_th:
            cv2.line(img, (int(xa), int(ya)), (int(xb), int(yb)), (255, 0, 0), 2)

def angle_3pts(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    nba = float(np.linalg.norm(ba))
    nbc = float(np.linalg.norm(bc))
    if nba < 1e-6 or nbc < 1e-6:
        return float("nan")
    cosang = float(np.dot(ba, bc) / (nba * nbc))
    cosang = max(-1.0, min(1.0, cosang))
    return math.degrees(math.acos(cosang))

@dataclass
class Joint3DState:
    xyz_raw: Optional[np.ndarray]
    xyz_filt: Optional[np.ndarray]
    v_xyz: Optional[np.ndarray]
    speed: Optional[float]
    valid: bool


# =========================
# Main
# =========================
def main():
    engine_path = os.getenv("ENGINE_PATH", "/home/a203/yolo11m-pose_fp16.engine")

    conf_th = float(os.getenv("CONF_TH", "0.25"))
    iou_th = float(os.getenv("IOU_TH", "0.45"))
    kp_th = float(os.getenv("KP_TH", "0.25"))

    hold_sec = float(os.getenv("HOLD_SEC", "0.5"))
    stick_iou = float(os.getenv("STICK_IOU", "0.2"))

    depth_roi = int(os.getenv("DEPTH_ROI", "5"))
    min_valid_ratio = float(os.getenv("DEPTH_MIN_VALID_RATIO", "0.25"))
    outlier_mad_k = float(os.getenv("DEPTH_OUTLIER_MAD_K", "3.5"))

    filt_min_cutoff = float(os.getenv("FILT_MIN_CUTOFF", "1.5"))
    filt_beta = float(os.getenv("FILT_BETA", "0.02"))
    filt_d_cutoff = float(os.getenv("FILT_D_CUTOFF", "1.0"))

    rgb_w = int(os.getenv("RGB_W", "640"))
    rgb_h = int(os.getenv("RGB_H", "480"))
    fps = int(os.getenv("FPS", "30"))

    trt_engine = TrtEngine(engine_path)

    filters_3d: Dict[int, OneEuroFilter3D] = {i: OneEuroFilter3D(filt_min_cutoff, filt_beta, filt_d_cutoff) for i in range(17)}
    prev_filt: Dict[int, Tuple[np.ndarray, float]] = {}

    st = TrackState()
    fps_ema = 0.0
    last_frame_t = time.time()

    win_name = "RealSense Depth + YOLO Pose TRT + 3D"

    try:
        with RealSenseAIApi(
            rgb_size=(rgb_w, rgb_h),
            depth_size=(rgb_w, rgb_h),
            fps=fps,
            enable_depth=True,
            align_depth_to="color",
            rgb_format="bgr",
            depth_hole_filling=1,
            depth_decimation=1,
            timeout_ms=2000,
        ) as cam:

            intr = cam.rgb_intrinsics()
            depth_scale = cam.depth_scale()
            if depth_scale is None:
                raise RuntimeError("Depth scale is None, depth stream not enabled?")

            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_name, 1280, 960)

            while True:
                bundle: FrameBundle = cam.get_frames(want_depth_frame=True, postprocess_depth=False)
                frame = bundle.rgb
                depth_z16 = bundle.depth
                if frame is None or depth_z16 is None:
                    continue

                inp, scale, dx, dy = preprocess_bgr_letterbox(frame, 640)
                out_trt = trt_engine.infer(inp)  # (1,56,8400)

                boxes, scores, kpts = decode_pose(out_trt, conf_th=conf_th, iou_th=iou_th)
                pick = pick_person(boxes, scores, kpts, st, stick_iou=stick_iou)

                now = time.time()

                if pick is None:
                    if st.kpts_640 is not None and (now - st.last_seen) <= hold_sec:
                        kpts_640 = st.kpts_640.copy()
                    else:
                        kpts_640 = None
                else:
                    bbox, sc, k_640 = pick
                    st.last_seen = now
                    st.bbox = bbox.copy()
                    st.kpts_640 = k_640.copy()
                    kpts_640 = st.kpts_640.copy()

                disp = frame.copy()
                joint_states: Dict[int, Joint3DState] = {}

                if kpts_640 is not None:
                    kpts_xy = unletterbox_points(kpts_640.reshape(-1, 3), scale, dx, dy)

                    draw_pose_2d(disp, kpts_xy, kp_th=kp_th)

                    for i in range(17):
                        x, y, s = kpts_xy[i]
                        if float(s) < kp_th:
                            joint_states[i] = Joint3DState(None, None, None, None, False)
                            continue

                        u = int(round(float(x)))
                        v = int(round(float(y)))

                        ds = robust_depth_at(
                            depth_z16=depth_z16,
                            depth_scale=depth_scale,
                            intr=intr,
                            u=u,
                            v=v,
                            roi=depth_roi,
                            min_valid_ratio=min_valid_ratio,
                            outlier_mad_k=outlier_mad_k
                        )

                        if not ds.valid or ds.xyz_m is None:
                            joint_states[i] = Joint3DState(None, None, None, None, False)
                            continue

                        xyz_raw = ds.xyz_m
                        xyz_filt = filters_3d[i](xyz_raw, now)

                        if i in prev_filt:
                            xyz_prev, t_prev = prev_filt[i]
                            dt = max(now - t_prev, 1e-6)
                            v_xyz = (xyz_filt - xyz_prev) / dt
                            speed = float(np.linalg.norm(v_xyz))
                        else:
                            v_xyz = None
                            speed = None

                        prev_filt[i] = (xyz_filt, now)
                        joint_states[i] = Joint3DState(xyz_raw, xyz_filt, v_xyz, speed, True)

                    def get3(i: int) -> Optional[np.ndarray]:
                        js = joint_states.get(i)
                        if js and js.valid and js.xyz_filt is not None:
                            return js.xyz_filt
                        return None

                    ytxt = 28
                    def put(line: str, color=(255, 255, 255)):
                        nonlocal ytxt
                        cv2.putText(disp, line, (10, ytxt), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        ytxt += 24

                    Ls = get3(COCO["L_SHOULDER"]); Le = get3(COCO["L_ELBOW"]); Lw = get3(COCO["L_WRIST"])
                    Rs = get3(COCO["R_SHOULDER"]); Re = get3(COCO["R_ELBOW"]); Rw = get3(COCO["R_WRIST"])
                    Lh = get3(COCO["L_HIP"]);      Lk = get3(COCO["L_KNEE"]);  La = get3(COCO["L_ANKLE"])
                    Rh = get3(COCO["R_HIP"]);      Rk = get3(COCO["R_KNEE"]);  Ra = get3(COCO["R_ANKLE"])

                    if Ls is not None and Le is not None and Lw is not None:
                        put(f"L elbow angle {angle_3pts(Ls, Le, Lw):.1f} deg")
                    if Rs is not None and Re is not None and Rw is not None:
                        put(f"R elbow angle {angle_3pts(Rs, Re, Rw):.1f} deg")
                    if Lh is not None and Lk is not None and La is not None:
                        put(f"L knee angle  {angle_3pts(Lh, Lk, La):.1f} deg")
                    if Rh is not None and Rk is not None and Ra is not None:
                        put(f"R knee angle  {angle_3pts(Rh, Rk, Ra):.1f} deg")

                    lw_state = joint_states.get(COCO["L_WRIST"])
                    rw_state = joint_states.get(COCO["R_WRIST"])
                    if lw_state and lw_state.valid and lw_state.speed is not None:
                        put(f"L wrist speed {lw_state.speed:.3f} m/s")
                    if rw_state and rw_state.valid and rw_state.speed is not None:
                        put(f"R wrist speed {rw_state.speed:.3f} m/s")

                cur_t = time.time()
                dt = max(cur_t - last_frame_t, 1e-6)
                last_frame_t = cur_t
                fps_inst = 1.0 / dt
                fps_ema = 0.9 * fps_ema + 0.1 * fps_inst

                cv2.putText(disp, f"FPS {fps_ema:.1f}  conf {conf_th}", (10, disp.shape[0] - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.imshow(win_name, disp)
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or key == ord("q"):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            trt_engine.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
