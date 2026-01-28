#!/usr/bin/env python3
import asyncio
import json
import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

import numpy as np
from aiohttp import ClientSession, WSMsgType
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.sdp import candidate_from_sdp
from aiortc.mediastreams import VideoStreamTrack
from av import VideoFrame


class LatestFrameBuffer:
    """
    sync thread(메인 처리 루프) -> async(webrtc track) 공유용
    최신 프레임 1장만 유지
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self._meta: Optional[Dict[str, Any]] = None
        self._updated_at: float = 0.0

    def push(self, frame_bgr: np.ndarray, meta: Optional[Dict[str, Any]] = None):
        with self._lock:
            self._frame = frame_bgr
            self._meta = meta
            self._updated_at = time.time()

    def pull(self) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]], float]:
        with self._lock:
            if self._frame is None:
                return None, None, 0.0
            frame = self._frame.copy()
            meta = (self._meta.copy() if self._meta else None)
            ts = self._updated_at
            return frame, meta, ts


class BufferVideoTrack(VideoStreamTrack):
    def __init__(self, buf: LatestFrameBuffer, target_fps: int = 15):
        super().__init__()
        self.buf = buf
        self.target_dt = 1.0 / float(max(1, target_fps))
        self.last_sent = 0.0

    async def recv(self):
        while True:
            now = time.time()
            if self.last_sent != 0.0:
                dt = now - self.last_sent
                if dt < self.target_dt:
                    await asyncio.sleep(self.target_dt - dt)
            self.last_sent = time.time()

            frame, _, _ = self.buf.pull()
            if frame is None:
                await asyncio.sleep(0.005)
                continue

            vf = VideoFrame.from_ndarray(frame, format="bgr24")
            vf.pts, vf.time_base = await self.next_timestamp()
            return vf


@dataclass
class WebRTCConfig:
    ws_url: str = "ws://0.0.0.0:8080/ws"
    fps: int = 15
    enable_telemetry: bool = True
    telemetry_hz: float = 10.0


class WebRTCStreamer:
    """
    signaling(ws) 통해 브라우저와 WebRTC 연결, buf의 최신 프레임을 비디오로 송출
    옵션, DataChannel로 frame meta를 보내고 echo로 RTT 측정
    """
    def __init__(self, buf: LatestFrameBuffer, cfg: WebRTCConfig):
        self.buf = buf
        self.cfg = cfg
        self._stop_ev = asyncio.Event()
        self._pc: Optional[RTCPeerConnection] = None
        self._dc = None

    def stop(self):
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self._stop_ev.set)
        except RuntimeError:
            pass

    async def _telemetry_loop(self):
        if not self._dc:
            return
        period = 1.0 / float(max(1e-6, self.cfg.telemetry_hz))
        while not self._stop_ev.is_set():
            frame, meta, _ = self.buf.pull()
            if meta is not None and self._dc and self._dc.readyState == "open":
                payload = {
                    "type": "frame_meta",
                    "frame_idx": int(meta.get("frame_idx", -1)),
                    "tx_ms": float(meta.get("host_ts_ms", time.time() * 1000.0)),
                }
                try:
                    self._dc.send(json.dumps(payload))
                except Exception:
                    pass
            await asyncio.sleep(period)

    async def run(self):
        pc = RTCPeerConnection()
        self._pc = pc

        track = BufferVideoTrack(self.buf, target_fps=self.cfg.fps)
        pc.addTrack(track)

        if self.cfg.enable_telemetry:
            self._dc = pc.createDataChannel("telemetry")

            @self._dc.on("message")
            def on_message(msg):
                # 브라우저 echo, {"type":"echo","frame_idx":..,"tx_ms":..,"rx_ms":..}
                try:
                    o = json.loads(msg)
                except Exception:
                    return
                if o.get("type") == "echo":
                    frame_idx = int(o.get("frame_idx", -1))
                    tx_ms = float(o.get("tx_ms", 0.0))
                    now_ms = time.time() * 1000.0
                    rtt_ms = now_ms - tx_ms
                    # print(f"[LAT] frame={frame_idx} rtt_ms={rtt_ms:.1f}")

        @pc.on("connectionstatechange")
        async def on_state():
            # print("[PC]", pc.connectionState)
            if pc.connectionState in ("failed", "closed", "disconnected"):
                self._stop_ev.set()

        async with ClientSession() as session:
            async with session.ws_connect(self.cfg.ws_url) as ws:
                await ws.send_str(json.dumps({"type": "jetson_hello"}))

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

                async def make_offer():
                    offer = await pc.createOffer()
                    await pc.setLocalDescription(offer)
                    await ws.send_str(json.dumps({
                        "type": "offer",
                        "sdp": {"type": pc.localDescription.type, "sdp": pc.localDescription.sdp}
                    }))

                tel_task = None

                async for m in ws:
                    if self._stop_ev.is_set():
                        break
                    if m.type != WSMsgType.TEXT:
                        continue

                    msg = json.loads(m.data)
                    t = msg.get("type")

                    if t == "browser_ready":
                        # print("[SIG] browser_ready -> offer")
                        await make_offer()
                        if self.cfg.enable_telemetry and tel_task is None:
                            tel_task = asyncio.create_task(self._telemetry_loop())

                    elif t == "answer":
                        sdp = msg["sdp"]
                        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp["sdp"], type=sdp["type"]))
                        # print("[SIG] answer set")

                    # elif t == "candidate":
                    #     c = msg["candidate"]
                    #     try:
                    #         cand = RTCIceCandidate(
                    #             sdpMid=c.get("sdpMid"),
                    #             sdpMLineIndex=c.get("sdpMLineIndex"),
                    #             candidate=c.get("candidate"),
                    #         )
                    #         await pc.addIceCandidate(cand)
                    #     except Exception as e:
                    #         print("[SIG] addIceCandidate error", e)

                    elif t == "candidate":
                        c = msg["candidate"]
                        try:
                            cand_s = c.get("candidate")

                            # 브라우저가 end-of-candidates를 null 또는 ""로 보내는 경우가 있음
                            # aiortc는 addIceCandidate(None)으로 종료 신호를 줄 수 있음
                            if not cand_s:
                                await pc.addIceCandidate(None)
                                continue

                            # JS candidate는 보통 "candidate:..."로 시작
                            # aiortc의 candidate_from_sdp는 "candidate:" prefix 없이 받는 형태라 strip 해줌
                            if cand_s.startswith("candidate:"):
                                cand_s = cand_s.split(":", 1)[1]

                            cand = candidate_from_sdp(cand_s)
                            cand.sdpMid = c.get("sdpMid")
                            cand.sdpMLineIndex = c.get("sdpMLineIndex")

                            await pc.addIceCandidate(cand)

                        except Exception as e:
                            print("[SIG] addIceCandidate error", e)

                if tel_task:
                    tel_task.cancel()
                    try:
                        await tel_task
                    except Exception:
                        pass

        await pc.close()
