#!/usr/bin/env python3
import asyncio
import json
import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

import numpy as np
from aiohttp import ClientSession, WSMsgType, WSServerHandshakeError, ClientConnectorError
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
        else:
            print("[STOP] stop() called but _loop is None")

    async def _telemetry_loop(self):
        if not self._dc:
            print("[TEL] no datachannel, telemetry disabled")
            return

        period = 1.0 / float(max(1e-6, self.cfg.telemetry_hz))
        print(f"[TEL] started hz={self.cfg.telemetry_hz} period={period:.3f}s")

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
                    except Exception as e:
                        print("[TEL] dc.send failed:", repr(e))

                await asyncio.sleep(period)

        except asyncio.CancelledError:
            print("[TEL] cancelled")
            return
        except Exception as e:
            print("[TEL] exception:", repr(e))
            return
        finally:
            print("[TEL] exited")

    async def run(self):
        self._loop = asyncio.get_running_loop()
        print("[RUN] start, ws_url =", self.cfg.ws_url)

        pc = RTCPeerConnection()
        self._pc = pc

        track = BufferVideoTrack(self.buf, target_fps=self.cfg.fps)
        pc.addTrack(track)

        tel_task: Optional[asyncio.Task] = None

        if self.cfg.enable_telemetry:
            self._dc = pc.createDataChannel("telemetry")
            print("[DC] created telemetry channel")

            @self._dc.on("open")
            def on_open():
                print("[DC] open")

            @self._dc.on("close")
            def on_close():
                print("[DC] close")

            @self._dc.on("message")
            def on_message(msg):
                # 브라우저 echo, {"type":"echo","frame_idx":..,"tx_ms":..,"rx_ms":..}
                try:
                    o = json.loads(msg)
                except Exception:
                    print("[DC] message (non-json):", str(msg)[:120])
                    return

                t = o.get("type")
                if t == "echo":
                    frame_idx = int(o.get("frame_idx", -1))
                    tx_ms = float(o.get("tx_ms", 0.0))
                    now_ms = time.time() * 1000.0
                    rtt_ms = now_ms - tx_ms
                    print(f"[DC] echo frame={frame_idx} rtt_ms={rtt_ms:.1f}")
                else:
                    print("[DC] message type:", t)

        @pc.on("connectionstatechange")
        async def on_state():
            print("[PC] connectionState:", pc.connectionState)
            if pc.connectionState in ("failed", "closed", "disconnected"):
                print("[STOP] set by pc state:", pc.connectionState)
                self._stop_ev.set()

        @pc.on("iceconnectionstatechange")
        async def on_ice_state():
            print("[PC] iceConnectionState:", pc.iceConnectionState)

        @pc.on("icegatheringstatechange")
        async def on_ice_gather():
            print("[PC] iceGatheringState:", pc.iceGatheringState)

        @pc.on("signalingstatechange")
        async def on_sig_state():
            print("[PC] signalingState:", pc.signalingState)

        try:
            async with ClientSession() as session:
                print("[WS] connecting...")
                try:
                    async with session.ws_connect(self.cfg.ws_url) as ws:
                        print("[WS] connected. sending jetson_hello")
                        await ws.send_str(json.dumps({"type": "jetson_hello"}))

                        @pc.on("icecandidate")
                        async def on_icecandidate(candidate):
                            if candidate:
                                # candidate.candidate는 "candidate:..." 포함
                                try:
                                    await ws.send_str(json.dumps({
                                        "type": "candidate",
                                        "candidate": {
                                            "candidate": candidate.candidate,
                                            "sdpMid": candidate.sdpMid,
                                            "sdpMLineIndex": candidate.sdpMLineIndex
                                        }
                                    }))
                                    # 너무 시끄러우면 아래 줄 주석
                                    # print("[ICE] sent candidate", candidate.sdpMid, candidate.sdpMLineIndex)
                                except Exception as e:
                                    print("[ICE] send candidate failed:", repr(e))
                            else:
                                # aiortc가 None을 올릴 수도 있음
                                # print("[ICE] candidate None (end-of-candidates)")
                                pass

                        async def make_offer():
                            print("[SIG] creating offer...")
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

                            if m.type == WSMsgType.TEXT:
                                try:
                                    msg = json.loads(m.data)
                                except Exception:
                                    print("[WS] TEXT but json parse failed:", m.data[:200])
                                    continue

                                t = msg.get("type")
                                print("[WS] recv type:", t)

                                if t == "browser_ready":
                                    print("[SIG] browser_ready -> make_offer")
                                    await make_offer()
                                    if self.cfg.enable_telemetry and tel_task is None:
                                        tel_task = asyncio.create_task(self._telemetry_loop())
                                        print("[TEL] task created")

                                elif t == "answer":
                                    sdp = msg["sdp"]
                                    print("[SIG] got answer -> setRemoteDescription")
                                    await pc.setRemoteDescription(
                                        RTCSessionDescription(sdp=sdp["sdp"], type=sdp["type"])
                                    )
                                    print("[SIG] answer set")

                                elif t == "candidate":
                                    c = msg.get("candidate", {})
                                    try:
                                        cand_s = c.get("candidate")

                                        if not cand_s:
                                            print("[ICE] recv end-of-candidates -> addIceCandidate(None)")
                                            await pc.addIceCandidate(None)
                                            continue

                                        if cand_s.startswith("candidate:"):
                                            cand_s2 = cand_s.split(":", 1)[1]
                                        else:
                                            cand_s2 = cand_s

                                        cand = candidate_from_sdp(cand_s2)
                                        cand.sdpMid = c.get("sdpMid")
                                        cand.sdpMLineIndex = c.get("sdpMLineIndex")

                                        await pc.addIceCandidate(cand)
                                        # print("[ICE] added candidate", cand.sdpMid, cand.sdpMLineIndex)

                                    except Exception as e:
                                        print("[SIG] addIceCandidate error:", repr(e))

                                else:
                                    # 서버가 close, ping, room, error 등 다른 타입을 보낼 수 있음
                                    print("[WS] unhandled msg:", msg)

                            elif m.type == WSMsgType.CLOSE:
                                print("[WS] CLOSE frame received")
                                break
                            elif m.type == WSMsgType.CLOSED:
                                print("[WS] CLOSED")
                                break
                            elif m.type == WSMsgType.ERROR:
                                print("[WS] ERROR:", repr(ws.exception()))
                                break
                            else:
                                # BINARY, PING, PONG 등
                                print("[WS] non-text msg type:", m.type)

                        print("[WS] loop ended. ws.closed =", ws.closed, "close_code =", ws.close_code)

                except WSServerHandshakeError as e:
                    print("[WS] handshake error:", repr(e))
                    raise
                except ClientConnectorError as e:
                    print("[WS] connect error:", repr(e))
                    raise

        except asyncio.CancelledError:
            print("[RUN] CancelledError -> set stop_ev")
            self._stop_ev.set()

        except Exception as e:
            print("[RUN] exception:", repr(e))
            self._stop_ev.set()

        finally:
            print("[RUN] cleanup start, stop_ev =", self._stop_ev.is_set())

            if tel_task:
                print("[TEL] cancelling task")
                tel_task.cancel()
                await asyncio.gather(tel_task, return_exceptions=True)

            try:
                print("[PC] closing...")
                await pc.close()
                print("[PC] closed")
            except Exception as e:
                print("[PC] close exception:", repr(e))

            print("[RUN] finished")
