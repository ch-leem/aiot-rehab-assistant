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

    # 중복 핸들러 방지(리로드/중복 실행 시 로그 두 번 찍히는 문제 방지)
    if logger.handlers:
        return logger

    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    # 콘솔 로그
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)

    # 파일 로그 (회전)
    fh = RotatingFileHandler(
        "signal.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
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
        self.jetson = None
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
        # 너무 시끄러우면 아래를 debug로 바꿔도 됨
        log.info(f"WS send {tag} type={obj.get('type')} bytes={len(payload)}")
    except Exception as e:
        log.exception(f"WS send failed tag={tag}: {e}")

# ------------------------
# Monitor: heartbeat timeout
# ------------------------
async def monitor_task(app):
    """
    주기적으로 Jetson heartbeat 체크.
    - heartbeat 안 오면 jetson에게 run/ping 요청
    - 브라우저에게 상태 알림
    """
    HEARTBEAT_TIMEOUT = 10.0  # 10초 동안 heartbeat 없으면 이상
    CHECK_INTERVAL = 2.0      # 2초마다 감시

    log.info(f"Monitor started (timeout={HEARTBEAT_TIMEOUT}s, interval={CHECK_INTERVAL}s)")

    while True:
        await asyncio.sleep(CHECK_INTERVAL)

        # jetson 연결 없음
        if hub.jetson is None or hub.jetson.closed:
            if hub.browser and not hub.browser.closed:
                await send_json(hub.browser, {"type": "jetson_status", "online": False}, tag="[monitor]")
            log.info("Monitor: jetson offline (no ws)")
            continue

        elapsed = now() - hub.last_jetson_seen if hub.last_jetson_seen else 1e9

        log.info(f"Monitor: jetson online, last_seen={elapsed:.1f}s ago")

        # 연결은 있는데 heartbeat가 오래 안 옴
        if elapsed > HEARTBEAT_TIMEOUT:
            log.warning(f"Monitor: heartbeat timeout ({elapsed:.1f}s) -> send run")

            # 1) 브라우저에게 경고
            await send_json(hub.browser, {
                "type": "jetson_status",
                "online": True,
                "warn": True,
                "reason": f"heartbeat timeout: {elapsed:.1f}s"
            }, tag="[monitor->browser]")

            # 2) jetson에게 run 트리거
            await send_json(hub.jetson, {
                "type": "run",
                "reason": "heartbeat_missing",
                "server_ts": time.time()
            }, tag="[monitor->jetson]")

# ------------------------
# WebSocket Handler
# ------------------------
async def ws_handler(request):
    peer = request.remote
    path = str(request.rel_url)
    log.info(f"WS connected from {peer} path={path}")

    # aiohttp ping/pong heartbeat (연결 생존성)
    ws = web.WebSocketResponse(heartbeat=15.0)
    await ws.prepare(request)

    role = None

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

            # --- 공통: last_seen 업데이트 ---
            if role == "jetson":
                hub.last_jetson_seen = now()
            elif role == "browser":
                hub.last_browser_seen = now()

            if t == "ready":
                role = "browser"
                hub.browser = ws
                hub.last_browser_seen = now()

                log.info("Browser ready")

                await send_json(ws, {"type": "info", "data": "browser ready"}, tag="[server->browser]")

                if hub.jetson and not hub.jetson.closed:
                    log.info("Browser ready: jetson is online -> notify both")
                    await send_json(hub.jetson, {"type": "browser_ready"}, tag="[server->jetson]")
                    await send_json(ws, {"type": "jetson_status", "online": True}, tag="[server->browser]")
                else:
                    log.info("Browser ready: jetson is offline")
                    await send_json(ws, {"type": "jetson_status", "online": False}, tag="[server->browser]")

            elif t == "jetson_hello" or t == "heartbeat_hello":
                role = "jetson"
                hub.jetson = ws
                hub.last_jetson_seen = now()

                log.info("Jetson connected (jetson_hello)")

                await send_json(ws, {"type": "info", "data": "jetson connected"}, tag="[server->jetson]")

                if hub.browser and not hub.browser.closed:
                    log.info("Jetson connected: browser online -> notify both")
                    await send_json(hub.browser, {"type": "info", "data": "jetson online"}, tag="[server->browser]")
                    await send_json(hub.browser, {"type": "jetson_status", "online": True}, tag="[server->browser]")
                    await send_json(ws, {"type": "browser_ready"}, tag="[server->jetson]")

            elif t == "heartbeat":
                if role == "jetson":
                    hub.last_jetson_seen = now()
                    # 너무 자주면 log.debug로 낮춰도 됨
                    log.info("Jetson heartbeat received")
                    await send_json(hub.browser, {"type": "jetson_hb", "ok": True}, tag="[jetson->browser]")
                else:
                    log.warning(f"Heartbeat received from non-jetson role={role}")

            elif t == "run":
                # 브라우저가 run 요청하면 jetson에게 전달
                if role == "browser":
                    log.info(f"Run requested by browser: {msg}")

                    if hub.jetson and not hub.jetson.closed:
                        await send_json(hub.jetson, msg, tag="[browser->jetson]")
                        log.info("Run forwarded to jetson")
                    else:
                        log.warning("Run requested but jetson offline")
                        await send_json(ws, {"type": "error", "message": "jetson offline"}, tag="[server->browser]")
                else:
                    log.info(f"Run received from role={role} (ignored or handle if needed) msg={msg}")
            
            elif t == "stop":
                # 브라우저가 run 요청하면 jetson에게 전달
                if role == "browser":
                    log.info(f"Run requested by browser: {msg}")

                    if hub.jetson and not hub.jetson.closed:
                        await send_json(hub.jetson, msg, tag="[browser->jetson]")
                        log.info("Run forwarded to jetson")
                    else:
                        log.warning("Run requested but jetson offline")
                        await send_json(ws, {"type": "error", "message": "jetson offline"}, tag="[server->browser]")
                else:
                    log.info(f"Run received from role={role} (ignored or handle if needed) msg={msg}")


            elif t in ("offer", "answer", "candidate"):
                # 시그널링 릴레이
                log.info(f"Signal relay {t} from role={role}")

                if role == "jetson" and hub.browser and not hub.browser.closed:
                    await send_json(hub.browser, msg, tag="[jetson->browser]")
                elif role == "browser" and hub.jetson and not hub.jetson.closed:
                    await send_json(hub.jetson, msg, tag="[browser->jetson]")
                else:
                    log.warning(f"Relay failed (no peer). type={t} from role={role}")

            else:
                log.info(f"Unhandled message type={t} role={role} msg_keys={list(msg.keys())}")

    except asyncio.CancelledError:
        log.warning(f"WS handler cancelled role={role} peer={peer}")
        raise
    except Exception as e:
        log.exception(f"WS handler exception role={role} peer={peer}: {e}")
    finally:
        log.info(f"WS closed role={role} peer={peer}")

        # 연결 종료 처리
        if role == "browser" and hub.browser is ws:
            hub.browser = None
            log.info("Hub: browser cleared")
        if role == "jetson" and hub.jetson is ws:
            hub.jetson = None
            log.info("Hub: jetson cleared")

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
