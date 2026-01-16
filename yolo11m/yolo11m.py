#!/usr/bin/env python3
import os
import time
import ctypes
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np
import tensorrt as trt

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

def cudaMemcpy(dst: int, src: int, nbytes: int, kind: int):
    err = _libcudart.cudaMemcpy(ctypes.c_void_p(dst), ctypes.c_void_p(src), ctypes.c_size_t(nbytes), kind)
    _check_cuda(err, "cudaMemcpy")

def cudaStreamCreate() -> int:
    stream = ctypes.c_void_p()
    err = _libcudart.cudaStreamCreate(ctypes.byref(stream))
    _check_cuda(err, "cudaStreamCreate")
    return stream.value

def cudaStreamDestroy(stream: int):
    err = _libcudart.cudaStreamDestroy(ctypes.c_void_p(stream))
    _check_cuda(err, "cudaStreamDestroy")

def cudaMemcpyAsync(dst: int, src: int, nbytes: int, kind: int, stream: int):
    err = _libcudart.cudaMemcpyAsync(ctypes.c_void_p(dst), ctypes.c_void_p(src), ctypes.c_size_t(nbytes), kind, ctypes.c_void_p(stream))
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

        # fixed shapes from your trtexec log:
        # input: images 1x3x640x640, output0 1x56x8400
        self.input_name = self.engine.get_tensor_name(0)
        self.output_name = self.engine.get_tensor_name(1)

        in_shape = tuple(self.engine.get_tensor_shape(self.input_name))
        out_shape = tuple(self.engine.get_tensor_shape(self.output_name))

        # Ensure NCHW fixed
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

        # Allocate
        self.stream = cudaStreamCreate()

        self.in_bytes = int(np.prod(self.input_shape) * np.dtype(self.io.input_dtype).itemsize)
        self.out_bytes = int(np.prod(self.output_shape) * np.dtype(self.io.output_dtype).itemsize)

        self.d_input = cudaMalloc(self.in_bytes)
        self.d_output = cudaMalloc(self.out_bytes)

        self.h_input = np.empty(self.input_shape, dtype=self.io.input_dtype)
        self.h_output = np.empty(self.output_shape, dtype=self.io.output_dtype)

        # Bind addresses
        self.context.set_tensor_address(self.input_name, self.d_input)
        self.context.set_tensor_address(self.output_name, self.d_output)

    def infer(self, input_nchw: np.ndarray) -> np.ndarray:
        # input_nchw: float32, shape (1,3,640,640)
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
# YOLO Pose postprocess (single-person tracking + smoothing)
# output: (1,56,8400)
# layout (Ultralytics pose):
#   0:4 bbox (cx,cy,w,h) in pixels on 640
#   4:5 obj conf
#   5:56 keypoints (17*3): x,y,score each (in pixels on 640)
# =========================
def nms_xywh(boxes_xywh: np.ndarray, scores: np.ndarray, iou_th: float) -> np.ndarray:
    # boxes: (N,4) cx,cy,w,h in pixels
    cx, cy, w, h = boxes_xywh[:,0], boxes_xywh[:,1], boxes_xywh[:,2], boxes_xywh[:,3]
    x1 = cx - w/2
    y1 = cy - h/2
    x2 = cx + w/2
    y2 = cy + h/2
    areas = (x2-x1) * (y2-y1)

    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        iw = np.maximum(0.0, xx2-xx1)
        ih = np.maximum(0.0, yy2-yy1)
        inter = iw*ih
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        inds = np.where(iou <= iou_th)[0]
        order = order[inds + 1]
    return np.array(keep, dtype=np.int32)

def decode_pose(output: np.ndarray,
                conf_th: float = 0.25,
                iou_th: float = 0.45) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    # output: (1,56,8400) float32
    pred = output[0].transpose(1,0)  # (8400,56)
    boxes = pred[:, 0:4]
    obj = pred[:, 4]
    kpts = pred[:, 5:].reshape(-1, 17, 3)

    m = obj >= conf_th
    boxes = boxes[m]
    obj = obj[m]
    kpts = kpts[m]

    if boxes.shape[0] == 0:
        return np.zeros((0,4), np.float32), np.zeros((0,), np.float32), np.zeros((0,17,3), np.float32)

    keep = nms_xywh(boxes, obj, iou_th)
    return boxes[keep], obj[keep], kpts[keep]

def iou_xywh(a: np.ndarray, b: np.ndarray) -> float:
    # cxcywh
    ax1, ay1 = a[0]-a[2]/2, a[1]-a[3]/2
    ax2, ay2 = a[0]+a[2]/2, a[1]+a[3]/2
    bx1, by1 = b[0]-b[2]/2, b[1]-b[3]/2
    bx2, by2 = b[0]+b[2]/2, b[1]+b[3]/2
    inter_x1, inter_y1 = max(ax1,bx1), max(ay1,by1)
    inter_x2, inter_y2 = min(ax2,bx2), min(ay2,by2)
    iw, ih = max(0.0, inter_x2-inter_x1), max(0.0, inter_y2-inter_y1)
    inter = iw*ih
    area_a = (ax2-ax1)*(ay2-ay1)
    area_b = (bx2-bx1)*(by2-by1)
    return inter / (area_a + area_b - inter + 1e-9)

@dataclass
class TrackState:
    bbox: Optional[np.ndarray] = None        # (4,) cxcywh on 640
    kpts: Optional[np.ndarray] = None        # (17,3)
    last_seen: float = 0.0

def pick_person(boxes: np.ndarray, scores: np.ndarray, kpts: np.ndarray, st: TrackState,
                stick_iou: float = 0.2) -> Optional[Tuple[np.ndarray, float, np.ndarray]]:
    if boxes.shape[0] == 0:
        return None

    if st.bbox is None:
        i = int(scores.argmax())
        return boxes[i], float(scores[i]), kpts[i]

    # pick by max IoU to previous, fallback to max score
    ious = np.array([iou_xywh(st.bbox, b) for b in boxes], dtype=np.float32)
    best = int(ious.argmax())
    if float(ious[best]) >= stick_iou:
        return boxes[best], float(scores[best]), kpts[best]
    i = int(scores.argmax())
    return boxes[i], float(scores[i]), kpts[i]

def ema(prev: np.ndarray, cur: np.ndarray, alpha: float) -> np.ndarray:
    return prev * alpha + cur * (1.0 - alpha)

def preprocess_bgr(frame_bgr: np.ndarray, size: int = 640) -> Tuple[np.ndarray, float, int, int]:
    h, w = frame_bgr.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((size, size, 3), dtype=np.uint8)
    dx = (size - nw) // 2
    dy = (size - nh) // 2
    canvas[dy:dy+nh, dx:dx+nw] = resized

    # to NCHW float32 0..1
    x = canvas.astype(np.float32) / 255.0
    x = x.transpose(2,0,1)[None, ...]  # (1,3,640,640)
    return x, scale, dx, dy

def unletterbox_points(kpts_640: np.ndarray, scale: float, dx: int, dy: int) -> np.ndarray:
    # kpts in 640 canvas pixels -> original image pixels
    out = kpts_640.copy()
    out[:, 0] = (out[:, 0] - dx) / (scale + 1e-9)
    out[:, 1] = (out[:, 1] - dy) / (scale + 1e-9)
    return out

def draw_pose(img: np.ndarray, kpts: np.ndarray, kp_th: float = 0.25):
    # simple skeleton (COCO-17)
    edges = [
        (5,7),(7,9), (6,8),(8,10),
        (5,6),
        (5,11),(6,12),
        (11,12),
        (11,13),(13,15),
        (12,14),(14,16),
        (0,1),(0,2),(1,3),(2,4)
    ]
    for i,(x,y,s) in enumerate(kpts):
        if s >= kp_th:
            cv2.circle(img, (int(x),int(y)), 3, (0,255,0), -1)
    for a,b in edges:
        xa,ya,sa = kpts[a]
        xb,yb,sb = kpts[b]
        if sa >= kp_th and sb >= kp_th:
            cv2.line(img, (int(xa),int(ya)), (int(xb),int(yb)), (255,0,0), 2)

def main():
    engine_path = "/home/a203/yolo11m-pose_fp16.engine"
    cam_index = int(os.getenv("CAM_INDEX", "4"))  # 너 로그에서 2번이 잡혔었음
    conf_th = float(os.getenv("CONF_TH", "0.25"))
    iou_th = float(os.getenv("IOU_TH", "0.45"))
    kp_th = float(os.getenv("KP_TH", "0.25"))
    smooth_alpha = float(os.getenv("SMOOTH_ALPHA", "0.75"))  # 0.7~0.9 권장, 클수록 더 매끈
    hold_sec = float(os.getenv("HOLD_SEC", "0.5"))          # 잠깐 못 잡혀도 유지

    trt_engine = TrtEngine(engine_path)

    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        raise RuntimeError(f"Camera open failed: index={cam_index}")

    st = TrackState()

    prev_t = time.time()
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        inp, scale, dx, dy = preprocess_bgr(frame, 640)
        out = trt_engine.infer(inp)  # (1,56,8400)

        boxes, scores, kpts = decode_pose(out, conf_th=conf_th, iou_th=iou_th)
        pick = pick_person(boxes, scores, kpts, st)

        now = time.time()

        if pick is None:
            # hold last pose for a short time to avoid flicker
            if st.kpts is not None and (now - st.last_seen) <= hold_sec:
                kpts_draw = st.kpts.copy()
            else:
                kpts_draw = None
        else:
            bbox, sc, k = pick
            st.last_seen = now
            st.bbox = bbox.copy()

            # smooth keypoints to avoid "disappear/appear" jitter
            if st.kpts is None:
                st.kpts = k.copy()
            else:
                st.kpts[:, :2] = ema(st.kpts[:, :2], k[:, :2], smooth_alpha)
                st.kpts[:, 2]  = ema(st.kpts[:, 2],  k[:, 2],  smooth_alpha)
            kpts_draw = st.kpts.copy()

        # draw
        disp = frame.copy()
        if kpts_draw is not None:
            kpts_xy = unletterbox_points(kpts_draw.reshape(-1,3), scale, dx, dy)
            draw_pose(disp, kpts_xy, kp_th=kp_th)

        # FPS
        cur_t = time.time()
        fps = 1.0 / max(1e-6, (cur_t - prev_t))
        prev_t = cur_t
        cv2.putText(disp, f"FPS {fps:.1f}  conf {conf_th}", (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

        cv2.imshow("YOLO11m-pose TRT FP16", disp)
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    trt_engine.close()

if __name__ == "__main__":
    main()
