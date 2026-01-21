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
from pose_sensor_fusion.vision.depth_lift import robust_depth_at, deproject_pixel_to_point_pinhole, DepthSample
from pose_sensor_fusion.vision.pose_2d_postprocessing import decode_pose, iou_xywh, TrackState, pick_person
from pose_sensor_fusion.vision.img_preprocessing import preprocess_bgr_letterbox, unletterbox_points
from pose_sensor_fusion.vision.visualize_pose import draw_pose_2d, angle_3pts, COCO, COCO_EDGES, Joint3DState


# =========================
# TRT wrapperclear
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
