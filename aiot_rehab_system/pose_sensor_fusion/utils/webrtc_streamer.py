#!/usr/bin/env python3
import asyncio
import json
import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

import numpy as np
from aiohttp import ClientSession, WSMsgType, ClientWebSocketResponse
from aiortc import RTCPeerConnection, RTCSessionDescription
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
    
    # 시그널링(ws)이 끊겨도 PC가 살아있으면 계속 송출 유지
    keep_streaming_on_ws_close: bool = True
    # 운영에서 ws가 자주 끊기면 재연결까지 하고 싶으면 True로
    reconnect_ws: bool = True
    reconnect_backoff_sec: float = 1.0


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
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def stop(self):
        if self._loop is not None:
            print("[STOP] set by stop() call")
            self._loop.call_soon_threadsafe(self._stop_ev.set)

    async def _telemetry_loop(self):
        if not self._dc:
            return

        period = 1.0 / float(max(1e-6, self.cfg.telemetry_hz))
        try:
            while not self._stop_ev.is_set():
                _, meta, _ = self.buf.pull()
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
        except asyncio.CancelledError:
            return

    async def _wait_pc_end(self, pc: RTCPeerConnection):
        # ws가 죽어도 pc가 살아있으면 계속 유지
        while not self._stop_ev.is_set():
            if pc.connectionState in ("failed", "closed", "disconnected"):
                return
            await asyncio.sleep(0.5)

    async def _run_once(self) -> None:
        pc = RTCPeerConnection()
        self._pc = pc

        track = BufferVideoTrack(self.buf, target_fps=self.cfg.fps)
        pc.addTrack(track)

        tel_task: Optional[asyncio.Task] = None

        if self.cfg.enable_telemetry:
            self._dc = pc.createDataChannel("telemetry")

            @self._dc.on("message")
            def on_message(msg):
                try:
                    o = json.loads(msg)
                except Exception:
                    return
                if o.get("type") == "echo":
                    frame_idx = int(o.get("frame_idx", -1))
                    tx_ms = float(o.get("tx_ms", 0.0))
                    now_ms = time.time() * 1000.0
                    rtt_ms = now_ms - tx_ms
                    print(f"[DC] echo frame={frame_idx} rtt_ms={rtt_ms:.1f}")

        @pc.on("connectionstatechange")
        async def on_state():
            print("[PC] connectionState:", pc.connectionState)
            if pc.connectionState in ("failed", "closed", "disconnected"):
                print("[STOP] set by pc state:", pc.connectionState)
                self._stop_ev.set()

        async with ClientSession() as session:
            async with session.ws_connect(self.cfg.ws_url) as ws:
                print("[WS] connected:", self.cfg.ws_url)
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
                    print("[SIG] offer sent")

                async for m in ws:
                    if self._stop_ev.is_set():
                        print("[SIG] stop event set, exiting ws loop")
                        break
                    if m.type != WSMsgType.TEXT:
                        continue

                    msg = json.loads(m.data)
                    t = msg.get("type")

                    if t == "browser_ready":
                        print("[SIG] browser_ready")
                        await make_offer()
                        if self.cfg.enable_telemetry and tel_task is None:
                            tel_task = asyncio.create_task(self._telemetry_loop())

                    elif t == "answer":
                        sdp = msg["sdp"]
                        await pc.setRemoteDescription(
                            RTCSessionDescription(sdp=sdp["sdp"], type=sdp["type"])
                        )
                        print("[SIG] answer set")

                    elif t == "candidate":
                        c = msg["candidate"]
                        cand_s = c.get("candidate")

                        if not cand_s:
                            await pc.addIceCandidate(None)
                            continue

                        if cand_s.startswith("candidate:"):
                            cand_s = cand_s.split(":", 1)[1]

                        cand = candidate_from_sdp(cand_s)
                        cand.sdpMid = c.get("sdpMid")
                        cand.sdpMLineIndex = c.get("sdpMLineIndex")

                        try:
                            await pc.addIceCandidate(cand)
                        except Exception as e:
                            print("[SIG] addIceCandidate error", e)

                print("[WS] loop ended. ws.closed =", ws.closed, "code =", ws.close_code)

        # 여기서부터가 핵심 변경점
        if self.cfg.keep_streaming_on_ws_close and pc.connectionState not in ("failed", "closed", "disconnected"):
            print("[KEEP] signaling ended, keep streaming until pc ends")
            await self._wait_pc_end(pc)

        # cleanup
        if tel_task:
            tel_task.cancel()
            await asyncio.gather(tel_task, return_exceptions=True)

        try:
            await pc.close()
        except Exception:
            pass

    async def run(self):
        self._loop = asyncio.get_running_loop()

        if not self.cfg.reconnect_ws:
            await self._run_once()
            return

        # 재연결 모드
        backoff = max(0.2, float(self.cfg.reconnect_backoff_sec))
        while not self._stop_ev.is_set():
            try:
                await self._run_once()
            except asyncio.CancelledError:
                self._stop_ev.set()
            except Exception as e:
                print("[RUN] ws/pc error:", repr(e))

            if self._stop_ev.is_set():
                break

            print(f"[RUN] reconnecting in {backoff:.1f}s...")
            await asyncio.sleep(backoff)
        print("[RUN] exited reconnect loop")