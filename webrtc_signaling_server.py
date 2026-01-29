#!/usr/bin/env python3
import json
import os
import ssl
import threading
from aiohttp import web

INDEX_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>WebRTC Signaling</title>
</head>
<body>
  <h3>WebRTC Signaling Server Running (WSS)</h3>
  <p>WebSocket endpoint: <code>/ws</code></p>
</body>
</html>
"""


class Hub:
  def __init__(self):
    self.browser = None
    self.jetson = None


hub = Hub()


async def index(request):
  return web.Response(text=INDEX_HTML, content_type="text/html")


async def ws_handler(request):
  ws = web.WebSocketResponse()
  await ws.prepare(request)

  role = None

  async for m in ws:
    if m.type != web.WSMsgType.TEXT:
      continue

    msg = json.loads(m.data)
    t = msg.get("type")

    if t == "ready":
      role = "browser"
      hub.browser = ws
      await ws.send_str(json.dumps({"type": "info", "data": "browser ready"}))
      if hub.jetson:
        await hub.jetson.send_str(json.dumps({"type": "browser_ready"}))

    elif t == "jetson_hello":
      role = "jetson"
      hub.jetson = ws
      await ws.send_str(json.dumps({"type": "info", "data": "jetson connected"}))
      if hub.browser:
        await hub.browser.send_str(json.dumps({"type": "info", "data": "jetson online"}))
        await ws.send_str(json.dumps({"type": "browser_ready"}))

    elif t in ("offer", "answer", "candidate"):
      if role == "jetson" and hub.browser:
        await hub.browser.send_str(json.dumps(msg))
      elif role == "browser" and hub.jetson:
        await hub.jetson.send_str(json.dumps(msg))

  if role == "browser" and hub.browser is ws:
    hub.browser = None
  if role == "jetson" and hub.jetson is ws:
    hub.jetson = None

  return ws


async def restart(request):
  def _exit():
    os._exit(0)

  threading.Timer(0.3, _exit).start()
  return web.json_response({"status": "restarting"})


def main():
  app = web.Application()
  app.router.add_get("/", index)
  app.router.add_get("/ws", ws_handler)
  app.router.add_post("/restart", restart)

  # TODO: update these paths to your cert and key
  ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
  ssl_ctx.load_cert_chain("C:/path/to/fullchain.pem", "C:/path/to/privkey.pem")

  web.run_app(app, host="0.0.0.0", port=8080, ssl_context=ssl_ctx)


if __name__ == "__main__":
  main()
