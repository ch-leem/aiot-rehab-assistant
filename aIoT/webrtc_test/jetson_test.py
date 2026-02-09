#!/usr/bin/env python3
import argparse
import asyncio
import ctypes
import json
import os
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np
import tensorrt as trt

from aiohttp import ClientSession, WSMsgType

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.mediastreams import VideoStreamTrack
from av import VideoFrame


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
TRT_LOGGER = trt.Logger(trt.Logger.ERROR)

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
# Postprocess + drawing
# =========================
def nms_xywh(boxes_xywh: np.ndarray, scores: np.ndarray, iou_th: float) -> np.ndarray:
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

def decode_pose(output: np.ndarray, conf_th: float = 0.25, iou_th: float = 0.45):
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
  bbox: Optional[np.ndarray] = None
  kpts: Optional[np.ndarray] = None
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

def ema(prev: np.ndarray, cur: np.ndarray, alpha: float) -> np.ndarray:
  return prev * alpha + cur * (1.0 - alpha)

def preprocess_bgr(frame_bgr: np.ndarray, size: int = 640):
  h, w = frame_bgr.shape[:2]
  scale = min(size / w, size / h)
  nw, nh = int(round(w * scale)), int(round(h * scale))
  resized = cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
  canvas = np.zeros((size, size, 3), dtype=np.uint8)
  dx = (size - nw) // 2
  dy = (size - nh) // 2
  canvas[dy:dy+nh, dx:dx+nw] = resized
  x = canvas.astype(np.float32) / 255.0
  x = x.transpose(2,0,1)[None, ...]
  return x, scale, dx, dy

def unletterbox_points(kpts_640: np.ndarray, scale: float, dx: int, dy: int) -> np.ndarray:
  out = kpts_640.copy()
  out[:, 0] = (out[:, 0] - dx) / (scale + 1e-9)
  out[:, 1] = (out[:, 1] - dy) / (scale + 1e-9)
  return out

def draw_pose(img: np.ndarray, kpts: np.ndarray, kp_th: float = 0.25):
  edges = [
    (5,7),(7,9), (6,8),(8,10),
    (5,6),
    (5,11),(6,12),
    (11,12),
    (11,13),(13,15),
    (12,14),(14,16),
    (0,1),(0,2),(1,3),(2,4)
  ]
  for (x,y,s) in kpts:
    if s >= kp_th:
      cv2.circle(img, (int(x),int(y)), 3, (0,255,0), -1)
  for a,b in edges:
    xa,ya,sa = kpts[a]
    xb,yb,sb = kpts[b]
    if sa >= kp_th and sb >= kp_th:
      cv2.line(img, (int(xa),int(ya)), (int(xb),int(yb)), (255,0,0), 2)


# =========================
# WebRTC video track
# =========================
class PoseVideoTrack(VideoStreamTrack):
  def __init__(self, cap, trt_engine: TrtEngine,
               conf_th: float, iou_th: float, kp_th: float,
               smooth_alpha: float, hold_sec: float, stick_iou: float,
               target_fps: int):
    super().__init__()
    self.cap = cap
    self.trt = trt_engine
    self.conf_th = conf_th
    self.iou_th = iou_th
    self.kp_th = kp_th
    self.smooth_alpha = smooth_alpha
    self.hold_sec = hold_sec
    self.stick_iou = stick_iou
    self.target_dt = 1.0 / float(target_fps)
    self.last_t = 0.0

    self.st = TrackState()

    self.prev_t = time.time()
    self.fps_ema = 0.0

  def process(self, frame_bgr: np.ndarray) -> np.ndarray:
    inp, scale, dx, dy = preprocess_bgr(frame_bgr, 640)
    out = self.trt.infer(inp)  # (1,56,8400)

    boxes, scores, kpts = decode_pose(out, conf_th=self.conf_th, iou_th=self.iou_th)
    pick = pick_person(boxes, scores, kpts, self.st, stick_iou=self.stick_iou)

    now = time.time()
    if pick is None:
      if self.st.kpts is not None and (now - self.st.last_seen) <= self.hold_sec:
        kpts_draw = self.st.kpts.copy()
      else:
        kpts_draw = None
    else:
      bbox, sc, k = pick
      self.st.last_seen = now
      self.st.bbox = bbox.copy()
      if self.st.kpts is None:
        self.st.kpts = k.copy()
      else:
        self.st.kpts[:, :2] = ema(self.st.kpts[:, :2], k[:, :2], self.smooth_alpha)
        self.st.kpts[:, 2]  = ema(self.st.kpts[:, 2],  k[:, 2],  self.smooth_alpha)
      kpts_draw = self.st.kpts.copy()

    disp = frame_bgr.copy()
    if kpts_draw is not None:
      kpts_xy = unletterbox_points(kpts_draw.reshape(-1,3), scale, dx, dy)
      draw_pose(disp, kpts_xy, kp_th=self.kp_th)

    cur_t = time.time()
    dt = max(1e-6, cur_t - self.prev_t)
    self.prev_t = cur_t
    fps_inst = 1.0 / dt
    self.fps_ema = 0.9 * self.fps_ema + 0.1 * fps_inst
    cv2.putText(disp, f"FPS {self.fps_ema:.1f} conf {self.conf_th}", (10,30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
    return disp

  async def recv(self):
    while True:
      now = time.time()
      if self.last_t != 0.0:
        dt = now - self.last_t
        if dt < self.target_dt:
          await asyncio.sleep(self.target_dt - dt)
      self.last_t = time.time()

      ok, frame = self.cap.read()
      if not ok or frame is None:
        await asyncio.sleep(0.01)
        continue

      disp = self.process(frame)
      vf = VideoFrame.from_ndarray(disp, format="bgr24")
      vf.pts, vf.time_base = await self.next_timestamp()
      return vf


async def run(ws_url: str,
              engine_path: str,
              cam_index: int, width: int, height: int, fps: int,
              conf_th: float, iou_th: float, kp_th: float,
              smooth_alpha: float, hold_sec: float, stick_iou: float):
  trt_engine = TrtEngine(engine_path)

  cap = cv2.VideoCapture(cam_index)
  if not cap.isOpened():
    trt_engine.close()
    raise RuntimeError(f"camera open failed index={cam_index}")

  cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
  cap.set(cv2.CAP_PROP_FPS, fps)

  pc = RTCPeerConnection()
  track = PoseVideoTrack(
    cap=cap,
    trt_engine=trt_engine,
    conf_th=conf_th, iou_th=iou_th, kp_th=kp_th,
    smooth_alpha=smooth_alpha, hold_sec=hold_sec, stick_iou=stick_iou,
    target_fps=fps,
  )
  pc.addTrack(track)

  async with ClientSession() as session:
    async with session.ws_connect(ws_url) as ws:
      await ws.send_str(json.dumps({ "type": "jetson_hello" }))

      @pc.on("icecandidate")
      async def on_icecandidate(candidate):
        if candidate:
          await ws.send_str(json.dumps({
            "type": "candidate",
            "candidate": {
              "candidate": candidate.candidate,
              "sdpMid": candidate.sdpMid,
              "sdpMLineIndex": candidate.sdpMLineIndex
            }
          }))

      @pc.on("connectionstatechange")
      async def on_state():
        print("[PC]", pc.connectionState)

      async def make_offer():
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await ws.send_str(json.dumps({
          "type": "offer",
          "sdp": {
            "type": pc.localDescription.type,
            "sdp": pc.localDescription.sdp
          }
        }))

      async for m in ws:
        if m.type != WSMsgType.TEXT:
          continue
        msg = json.loads(m.data)
        t = msg.get("type")

        if t == "browser_ready":
          print("[SIG] browser_ready -> offer")
          await make_offer()

        elif t == "answer":
          sdp = msg["sdp"]
          await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp["sdp"], type=sdp["type"]))
          print("[SIG] answer set")

        elif t == "candidate":
          c = msg["candidate"]
          try:
            cand = RTCIceCandidate(
              sdpMid=c.get("sdpMid"),
              sdpMLineIndex=c.get("sdpMLineIndex"),
              candidate=c.get("candidate"),
            )
            await pc.addIceCandidate(cand)
          except Exception as e:
            print("[SIG] addIceCandidate error", e)

  await pc.close()
  cap.release()
  trt_engine.close()


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--ws", default="ws://0.0.0.0:8080/ws")
  ap.add_argument("--engine", default="/home/a203/yolo11m-pose_fp16.engine")
  ap.add_argument("--cam", type=int, default=int(os.getenv("CAM_INDEX", "4")))
  ap.add_argument("--w", type=int, default=640)
  ap.add_argument("--h", type=int, default=360)
  ap.add_argument("--fps", type=int, default=15)

  ap.add_argument("--conf", type=float, default=0.25)
  ap.add_argument("--iou", type=float, default=0.45)
  ap.add_argument("--kp", type=float, default=0.25)

  ap.add_argument("--smooth", type=float, default=0.75)
  ap.add_argument("--hold", type=float, default=0.5)
  ap.add_argument("--stick_iou", type=float, default=0.2)

  args = ap.parse_args()

  asyncio.run(run(
    ws_url=args.ws,
    engine_path=args.engine,
    cam_index=args.cam, width=args.w, height=args.h, fps=args.fps,
    conf_th=args.conf, iou_th=args.iou, kp_th=args.kp,
    smooth_alpha=args.smooth, hold_sec=args.hold, stick_iou=args.stick_iou
  ))

if __name__ == "__main__":
  main()
