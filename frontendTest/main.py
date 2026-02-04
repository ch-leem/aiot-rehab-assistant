#!/usr/bin/env python3
import json
import time
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from aiohttp import web, WSMsgType

# ------------------------
# Logging
# ------------------------
def setup_logging():
    logger = logging.getLogger("signal")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)

    fh = RotatingFileHandler(
        "signal.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    fh.setFormatter(fmt)

    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger


log = setup_logging()

# ------------------------
# HTML
# ------------------------
INDEX_HTML = r"""(생략: 네 HTML 그대로)"""

# ------------------------
# State Hub
# ------------------------
class Hub:
    def __init__(self):
        self.browser = None
        self.jetson_webrtc = None
        self.jetson_heartbeat = None
        self.last_jetson_seen = 0.0
        self.last_browser_seen = 0.0


hub = Hub()


def now():
    return time.monotonic()


async def index(request):
    peer = request.remote
    log.info(f"HTTP GET / from {peer}")
    return web.Response(text=INDEX_HTML, content_type="text/html")


async def send_json(ws, obj, tag=""):
    if ws is None:
        log.debug(f"send_json skipped (ws=None) tag={tag} obj={obj}")
        return
    if ws.closed:
        log.debug(f"send_json skipped (ws.closed) tag={tag} obj={obj}")
        return

    payload = json.dumps(obj)
    try:
        await ws.send_str(payload)
        log.info(f"WS send {tag} type={obj.get('type')} bytes={len(payload)}")
    except Exception as e:
        log.exception(f"WS send failed tag={tag}: {e}")


def jetson_online():
    return (
        hub.jetson_webrtc is not None and not hub.jetson_webrtc.closed
        and hub.jetson_heartbeat is not None and not hub.jetson_heartbeat.closed
    )


# ------------------------
# Monitor: heartbeat timeout
# ------------------------
async def monitor_task(app):
    HEARTBEAT_TIMEOUT = 10.0
    CHECK_INTERVAL = 2.0

    log.info(f"Monitor started (timeout={HEARTBEAT_TIMEOUT}s, interval={CHECK_INTERVAL}s)")

    while True:
        await asyncio.sleep(CHECK_INTERVAL)

        hb_ws = hub.jetson_heartbeat
        if hb_ws is None or hb_ws.closed:
            if hub.browser and not hub.browser.closed:
                await send_json(hub.browser, {"type": "jetson_status", "online": False}, tag="[monitor]")
            log.info("Monitor: jetson heartbeat offline (no ws)")
            continue

        elapsed = now() - hub.last_jetson_seen if hub.last_jetson_seen else 1e9
        log.info(f"Monitor: last_jetson_seen={elapsed:.1f}s ago")

        if elapsed > HEARTBEAT_TIMEOUT:
            log.warning(f"Monitor: heartbeat timeout ({elapsed:.1f}s) -> send run to control channel")

            if hub.browser and not hub.browser.closed:
                await send_json(hub.browser, {
                    "type": "jetson_status",
                    "online": True,
                    "warn": True,
                    "reason": f"heartbeat timeout: {elapsed:.1f}s",
                }, tag="[monitor->browser]")

            await send_json(hb_ws, {
                "type": "run",
                "reason": "heartbeat_missing",
                "server_ts": time.time(),
            }, tag="[monitor->jetson_ctrl]")


# ------------------------
# WebSocket Handler
# ------------------------
async def ws_handler(request):
    peer = request.remote
    path = str(request.rel_url)
    log.info(f"WS connected from {peer} path={path}")

    ws = web.WebSocketResponse(heartbeat=15.0)
    await ws.prepare(request)

    role = None  # "browser", "jetson_webrtc", "jetson_heartbeat"

    try:
        async for m in ws:
            if m.type != WSMsgType.TEXT:
                log.info(f"WS recv non-text type={m.type} from {peer} role={role}")
                continue

            raw = m.data
            try:
                msg = json.loads(raw)
            except Exception:
                log.warning(f"WS invalid json from {peer} role={role}: {raw[:200]}")
                continue

            t = msg.get("type")
            log.info(f"WS recv role={role or 'unknown'} type={t} from {peer}")

            # last_seen 업데이트
            if role in ("jetson_webrtc", "jetson_heartbeat"):
                # 실제 heartbeat는 jetson_heartbeat에서 오므로 그걸 기준으로 갱신하지만
                # 연결 생존 자체는 둘 다 참고할 수 있어서 여기서도 업데이트는 해 둠
                hub.last_jetson_seen = now()
            elif role == "browser":
                hub.last_browser_seen = now()

            # ------------------------
            # Browser hello
            # ------------------------
            if t == "ready":
                role = "browser"
                hub.browser = ws
                hub.last_browser_seen = now()

                log.info("Browser ready")
                await send_json(ws, {"type": "info", "data": "browser ready"}, tag="[server->browser]")

                online = jetson_online()
                await send_json(ws, {"type": "jetson_status", "online": online}, tag="[server->browser]")

                if hub.jetson_webrtc and not hub.jetson_webrtc.closed:
                    await send_json(hub.jetson_webrtc, {"type": "browser_ready"}, tag="[server->jetson_webrtc]")

                continue

            # ------------------------
            # Jetson webrtc hello
            # ------------------------
            if t == "jetson_hello":
                role = "jetson_webrtc"
                hub.jetson_webrtc = ws
                hub.last_jetson_seen = now()

                log.info("Jetson WebRTC connected (jetson_hello)")
                await send_json(ws, {"type": "info", "data": "jetson webrtc connected"}, tag="[server->jetson_webrtc]")

                if hub.browser and not hub.browser.closed:
                    await send_json(hub.browser, {"type": "info", "data": "jetson webrtc online"}, tag="[server->browser]")
                    await send_json(hub.browser, {"type": "jetson_status", "online": jetson_online()}, tag="[server->browser]")
                    await send_json(ws, {"type": "browser_ready"}, tag="[server->jetson_webrtc]")

                continue

            # ------------------------
            # Jetson heartbeat/control hello
            # ------------------------
            if t == "heartbeat_hello":
                role = "jetson_heartbeat"
                hub.jetson_heartbeat = ws
                hub.last_jetson_seen = now()

                log.info("Jetson Heartbeat connected (heartbeat_hello)")
                await send_json(ws, {"type": "info", "data": "jetson heartbeat connected"}, tag="[server->jetson_hb]")

                if hub.browser and not hub.browser.closed:
                    await send_json(hub.browser, {"type": "info", "data": "jetson heartbeat online"}, tag="[server->browser]")
                    await send_json(hub.browser, {"type": "jetson_status", "online": jetson_online()}, tag="[server->browser]")

                continue

            # ------------------------
            # Heartbeat message
            # ------------------------
            if t == "heartbeat":
                if role == "jetson_heartbeat":
                    hub.last_jetson_seen = now()
                    log.info("Jetson heartbeat received")
                    if hub.browser and not hub.browser.closed:
                        await send_json(hub.browser, {"type": "jetson_hb", "ok": True}, tag="[jetson_hb->browser]")
                else:
                    log.warning(f"Heartbeat received from non-jetson_heartbeat role={role}")
                continue

            # ------------------------
            # Run / Stop from browser -> control channel
            # ------------------------
            if t in ("run", "stop"):
                if role == "browser":
                    target = hub.jetson_heartbeat  # 제어는 heartbeat.py가 받는 구조 기준
                    if target and not target.closed:
                        await send_json(target, msg, tag="[browser->jetson_ctrl]")
                        log.info(f"{t} forwarded to jetson control channel")
                    else:
                        log.warning(f"{t} requested but jetson control offline")
                        await send_json(ws, {"type": "error", "message": "jetson control offline"}, tag="[server->browser]")
                else:
                    log.info(f"{t} received from role={role} (ignored) msg={msg}")
                continue

            # ------------------------
            # Signaling relay: browser <-> jetson_webrtc only
            # ------------------------
            if t in ("offer", "answer", "candidate"):
                log.info(f"Signal relay {t} from role={role}")

                if role == "jetson_webrtc":
                    if hub.browser and not hub.browser.closed:
                        await send_json(hub.browser, msg, tag="[jetson_webrtc->browser]")
                    else:
                        log.warning(f"Relay failed, no browser. type={t}")
                elif role == "browser":
                    if hub.jetson_webrtc and not hub.jetson_webrtc.closed:
                        await send_json(hub.jetson_webrtc, msg, tag="[browser->jetson_webrtc]")
                    else:
                        log.warning(f"Relay failed, no jetson_webrtc. type={t}")
                else:
                    log.warning(f"Relay ignored, role={role}, type={t}")
                continue

            log.info(f"Unhandled message type={t} role={role} msg_keys={list(msg.keys())}")

    except asyncio.CancelledError:
        log.warning(f"WS handler cancelled role={role} peer={peer}")
        raise
    except Exception as e:
        log.exception(f"WS handler exception role={role} peer={peer}: {e}")
    finally:
        log.info(f"WS closed role={role} peer={peer}")

        if role == "browser" and hub.browser is ws:
            hub.browser = None
            log.info("Hub: browser cleared")

        if role == "jetson_webrtc" and hub.jetson_webrtc is ws:
            hub.jetson_webrtc = None
            log.info("Hub: jetson_webrtc cleared")

        if role == "jetson_heartbeat" and hub.jetson_heartbeat is ws:
            hub.jetson_heartbeat = None
            log.info("Hub: jetson_heartbeat cleared")

        if hub.browser and not hub.browser.closed:
            await send_json(hub.browser, {"type": "jetson_status", "online": jetson_online()}, tag="[server->browser]")

    return ws


# ------------------------
# App bootstrap
# ------------------------
async def on_startup(app):
    log.info("App startup")
    app["monitor_task"] = asyncio.create_task(monitor_task(app))


async def on_cleanup(app):
    log.info("App cleanup")
    t = app.get("monitor_task")
    if t:
        t.cancel()
        try:
            await t
        except Exception:
            pass


def main():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    log.info("Starting server on 0.0.0.0:8080")
    web.run_app(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()

