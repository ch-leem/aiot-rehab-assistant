#!/usr/bin/env python3
import json
from aiohttp import web

INDEX_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>WebRTC Signaling</title>
</head>
<body>
  <h3>WebRTC Signaling Server Running</h3>
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


def main():
  app = web.Application()
  app.router.add_get("/", index)
  app.router.add_get("/ws", ws_handler)
  web.run_app(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
  main()
