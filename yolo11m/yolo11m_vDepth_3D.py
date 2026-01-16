#!/usr/bin/env python3
import os
import time
import math
import ctypes
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

import cv2
import numpy as np
import tensorrt as trt
import open3d as o3d

from realsense_ai_api import RealSenseAIApi, FrameBundle, Intrinsics


# =========================
# CUDA Runtime via ctypes (no pycuda)
# =========================
_libcudart = ctypes.CDLL("libcudart.so")

cudaSuccess = 0
cudaMemcpyHostToDevice = 1
cudaMemcpyDeviceToHost = 2

def _check_cuda(err: int, msg: str):
    if err != cudaSuccess:
        raise RuntimeError(f"CUDA error {err} at {msg}")

def cudaMalloc(nbytes: int) -> int:
    ptr = ctypes.c_void_p()
    err = _libcudart.cudaMalloc(ctypes.byref(ptr), ctypes.c_size_t(nbytes))
    _check_cuda(err, "cudaMalloc")
    return ptr.value

def cudaFree(ptr: int):
    err = _libcudart.cudaFree(ctypes.c_void_p(ptr))
    _check_cuda(err, "cudaFree")

def cudaStreamCreate() -> int:
    stream = ctypes.c_void_p()
    err = _libcudart.cudaStreamCreate(ctypes.byref(stream))
    _check_cuda(err, "cudaStreamCreate")
    return stream.value

def cudaStreamDestroy(stream: int):
    err = _libcudart.cudaStreamDestroy(ctypes.c_void_p(stream))
    _check_cuda(err, "cudaStreamDestroy")

def cudaMemcpyAsync(dst: int, src: int, nbytes: int, kind: int, stream: int):
    err = _libcudart.cudaMemcpyAsync(
        ctypes.c_void_p(dst),
        ctypes.c_void_p(src),
        ctypes.c_size_t(nbytes),
        kind,
        ctypes.c_void_p(stream),
    )
    _check_cuda(err, "cudaMemcpyAsync")

def cudaStreamSynchronize(stream: int):
    err = _libcudart.cudaStreamSynchronize(ctypes.c_void_p(stream))
    _check_cuda(err, "cudaStreamSynchronize")


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
# One Euro Filter (3D)
# =========================
class OneEuroFilter1D:
    def __init__(self, min_cutoff=1.5, beta=0.02, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    @staticmethod
    def _alpha(cutoff_hz: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff_hz)
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def __call__(self, x: float, t: float) -> float:
        if self.t_prev is None or self.x_prev is None:
            self.t_prev = t
            self.x_prev = float(x)
            self.dx_prev = 0.0
            return float(x)

        dt = max(t - self.t_prev, 1e-6)

        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)

        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat

class OneEuroFilter3D:
    def __init__(self, min_cutoff=1.5, beta=0.02, d_cutoff=1.0):
        self.fx = OneEuroFilter1D(min_cutoff, beta, d_cutoff)
        self.fy = OneEuroFilter1D(min_cutoff, beta, d_cutoff)
        self.fz = OneEuroFilter1D(min_cutoff, beta, d_cutoff)

    def reset(self):
        self.fx.reset()
        self.fy.reset()
        self.fz.reset()

    def __call__(self, xyz: np.ndarray, t: float) -> np.ndarray:
        return np.array(
            [self.fx(float(xyz[0]), t), self.fy(float(xyz[1]), t), self.fz(float(xyz[2]), t)],
            dtype=np.float32,
        )


# =========================
# Depth robust sampling + deprojection
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

    final = med if kept.size < max(3, int(vals.size * 0.2)) else float(np.median(kept))
    z_m = final * depth_scale
    xyz = deproject_pixel_to_point_pinhole(intr, u, v, z_m)
    return DepthSample(z_m, xyz, True, "")


# =========================
# YOLO Pose postprocess
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
    x = x.transpose(2, 0, 1)[None, ...]
    return x, scale, dx, dy

def unletterbox_points(kpts_640: np.ndarray, scale: float, dx: int, dy: int) -> np.ndarray:
    out = kpts_640.copy()
    out[:, 0] = (out[:, 0] - dx) / (scale + 1e-9)
    out[:, 1] = (out[:, 1] - dy) / (scale + 1e-9)
    return out


# =========================
# COCO-17 skeleton
# =========================
COCO_EDGES = [
    (5, 7), (7, 9),
    (6, 8), (8, 10),
    (5, 6),
    (5, 11), (6, 12),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (0, 1), (0, 2), (1, 3), (2, 4),
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


# =========================
# Open3D helpers
# =========================
def cam_xyz_to_o3d(xyz_cam_m: np.ndarray) -> np.ndarray:
    x, y, z = float(xyz_cam_m[0]), float(xyz_cam_m[1]), float(xyz_cam_m[2])
    return np.array([x, -y, z], dtype=np.float64)

def build_lineset(points: np.ndarray) -> o3d.geometry.LineSet:
    ls = o3d.geometry.LineSet()
    ls.points = o3d.utility.Vector3dVector(points.astype(np.float64))
    ls.lines = o3d.utility.Vector2iVector(np.array(COCO_EDGES, dtype=np.int32))
    colors = np.tile(np.array([[0.2, 0.9, 0.2]], dtype=np.float64), (len(COCO_EDGES), 1))
    ls.colors = o3d.utility.Vector3dVector(colors)
    return ls


def main():
    engine_path = os.getenv("ENGINE_PATH", "/home/a203/yolo11m-pose_fp16.engine")

    conf_th = float(os.getenv("CONF_TH", "0.25"))
    iou_th = float(os.getenv("IOU_TH", "0.45"))
    kp_th = float(os.getenv("KP_TH", "0.25"))
    stick_iou = float(os.getenv("STICK_IOU", "0.2"))
    hold_sec = float(os.getenv("HOLD_SEC", "0.5"))

    depth_roi = int(os.getenv("DEPTH_ROI", "5"))

    filt_min_cutoff = float(os.getenv("FILT_MIN_CUTOFF", "1.5"))
    filt_beta = float(os.getenv("FILT_BETA", "0.02"))
    filt_d_cutoff = float(os.getenv("FILT_D_CUTOFF", "1.0"))

    rgb_w = int(os.getenv("RGB_W", "640"))
    rgb_h = int(os.getenv("RGB_H", "480"))
    fps = int(os.getenv("FPS", "30"))

    show_2d = int(os.getenv("SHOW_2D", "1")) == 1
    show_3d = int(os.getenv("SHOW_3D", "1")) == 1

    trt_engine = TrtEngine(engine_path)

    filters_3d: Dict[int, OneEuroFilter3D] = {
        i: OneEuroFilter3D(filt_min_cutoff, filt_beta, filt_d_cutoff) for i in range(17)
    }

    st = TrackState()
    fps_ema = 0.0
    last_t = time.time()

    win2d = "2D (YOLO pose)"
    win3d = "3D skeleton (Depth deprojected)"

    vis = None
    ls = None
    pts_geom = None
    cam_inited = False

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

            if show_2d:
                cv2.namedWindow(win2d, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(win2d, 1280, 960)

            if show_3d:
                vis = o3d.visualization.Visualizer()
                vis.create_window(window_name=win3d, width=1000, height=800)

                axis = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.05, origin=[0, 0, 0])
                vis.add_geometry(axis)

                init_points = np.zeros((17, 3), dtype=np.float64)
                ls = build_lineset(init_points)

                pts_geom = o3d.geometry.PointCloud()
                pts_geom.points = o3d.utility.Vector3dVector(init_points)
                pts_geom.paint_uniform_color([0.95, 0.2, 0.2])

                vis.add_geometry(ls)
                vis.add_geometry(pts_geom)

                opt = vis.get_render_option()
                opt.point_size = 10.0
                opt.line_width = 5.0

                ctr = vis.get_view_control()
                ctr.set_zoom(0.6)

            while True:
                bundle: FrameBundle = cam.get_frames(want_depth_frame=True, postprocess_depth=False)
                frame = bundle.rgb
                depth_z16 = bundle.depth
                if frame is None or depth_z16 is None:
                    continue

                inp, scale, dx, dy = preprocess_bgr_letterbox(frame, 640)
                out_trt = trt_engine.infer(inp)

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

                points3d_o3d = np.zeros((17, 3), dtype=np.float64)
                valid_mask = np.zeros((17,), dtype=bool)

                if kpts_640 is not None:
                    kpts_xy = unletterbox_points(kpts_640.reshape(-1, 3), scale, dx, dy)

                    if show_2d:
                        draw_pose_2d(disp, kpts_xy, kp_th=kp_th)

                    for i in range(17):
                        x, y, s = kpts_xy[i]
                        if float(s) < kp_th:
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
                            min_valid_ratio=0.25,
                            outlier_mad_k=3.5,
                        )
                        if not ds.valid or ds.xyz_m is None:
                            continue

                        xyz_filt = filters_3d[i](ds.xyz_m, now)
                        points3d_o3d[i] = cam_xyz_to_o3d(xyz_filt)
                        valid_mask[i] = True

                # FPS
                cur = time.time()
                dt = max(cur - last_t, 1e-6)
                last_t = cur
                fps_inst = 1.0 / dt
                fps_ema = 0.9 * fps_ema + 0.1 * fps_inst

                if show_2d:
                    cv2.putText(
                        disp,
                        f"FPS {fps_ema:.1f} conf {conf_th}",
                        (10, disp.shape[0] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )
                    cv2.imshow(win2d, disp)
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27 or key == ord("q"):
                        break

                if show_3d and vis is not None and ls is not None and pts_geom is not None:
                    if valid_mask.any():
                        ls.points = o3d.utility.Vector3dVector(points3d_o3d)
                        pts_geom.points = o3d.utility.Vector3dVector(points3d_o3d)

                        vis.update_geometry(ls)
                        vis.update_geometry(pts_geom)

                        if not cam_inited:
                            vis.reset_view_point(True)
                            cam_inited = True

                        center = points3d_o3d[valid_mask].mean(axis=0)
                        ctr = vis.get_view_control()
                        ctr.set_lookat(center.tolist())

                    vis.poll_events()
                    vis.update_renderer()

    except KeyboardInterrupt:
        pass
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            if vis is not None:
                vis.destroy_window()
        except Exception:
            pass
        try:
            trt_engine.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
