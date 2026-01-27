#!/usr/bin/env python3
import json
from aiohttp import web

INDEX_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Jetson WebRTC Pose Demo</title>
  <style>
    body { font-family: sans-serif; margin: 16px; }
    video { width: 100%; max-width: 960px; background: #000; }
    button { padding: 10px 14px; margin-right: 8px; }
    pre { background: #111; color: #0f0; padding: 12px; max-width: 960px; overflow: auto; }
  </style>
</head>
<body>
  <h2>Jetson WebRTC Pose Demo</h2>
  <div>
    <button id="btnStart">Start</button>
    <button id="btnStop">Stop</button>
  </div>
  <p>상태, <span id="status">idle</span></p>
  <video id="video" autoplay playsinline controls muted></video>
  <h3>Logs</h3>
  <pre id="log"></pre>

<script>
let pc = null;
let ws = null;

function log(msg) {
  const el = document.getElementById("log");
  el.textContent += msg + "\n";
  el.scrollTop = el.scrollHeight;
}
function setStatus(s) {
  document.getElementById("status").textContent = s;
}

async function start() {
  if (pc) return;

  setStatus("connecting");
  const scheme = (location.protocol === "https:") ? "wss" : "ws";
  ws = new WebSocket(`${scheme}://${location.host}/test/ws`);
  
  ws.onopen = async () => {
    log("WS connected");

    pc = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
    });

    // DataChannel (telemetry) 수신, echo 반환
    pc.ondatachannel = (ev) => {
      const ch = ev.channel;
      log("datachannel: " + ch.label);

      ch.onmessage = (e) => {
        let o = null;
        try { o = JSON.parse(e.data); } catch {}
        if (!o) return;

        if (o.type === "frame_meta") {
          ch.send(JSON.stringify({
            type: "echo",
            frame_idx: o.frame_idx,
            tx_ms: o.tx_ms,
            rx_ms: performance.now()
          }));
        }
      };
    };

    pc.ontrack = (event) => {
      log("track received");
      const video = document.getElementById("video");
      if (video.srcObject !== event.streams[0]) {
        video.srcObject = event.streams[0];
      }
    };

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        ws.send(JSON.stringify({ type: "candidate", candidate: event.candidate }));
      }
    };

    pc.onconnectionstatechange = () => {
      log("pc state: " + pc.connectionState);
      setStatus(pc.connectionState);
    };

    ws.send(JSON.stringify({ type: "ready" }));
  };

  ws.onmessage = async (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.type === "offer") {
      log("offer received");
      await pc.setRemoteDescription(msg.sdp);
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      ws.send(JSON.stringify({ type: "answer", sdp: pc.localDescription }));
    } else if (msg.type === "candidate") {
      try {
        await pc.addIceCandidate(msg.candidate);
      } catch (e) {
        log("addIceCandidate error: " + e);
      }
    } else if (msg.type === "info") {
      log("info: " + msg.data);
    }
  };

  ws.onclose = () => log("WS closed");
}

async function stop() {
  setStatus("stopping");
  if (ws) { ws.close(); ws = null; }
  if (pc) { pc.close(); pc = null; }
  document.getElementById("video").srcObject = null;
  setStatus("idle");
  log("stopped");
}

document.getElementById("btnStart").onclick = start;
document.getElementById("btnStop").onclick = stop;
</script>
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
      await ws.send_str(json.dumps({ "type": "info", "data": "browser ready" }))
      if hub.jetson:
        await hub.jetson.send_str(json.dumps({ "type": "browser_ready" }))

    elif t == "jetson_hello":
      role = "jetson"
      hub.jetson = ws
      await ws.send_str(json.dumps({ "type": "info", "data": "jetson connected" }))
      if hub.browser:
        await hub.browser.send_str(json.dumps({ "type": "info", "data": "jetson online" }))
        await ws.send_str(json.dumps({ "type": "browser_ready" }))

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

