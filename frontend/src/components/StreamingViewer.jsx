import { useEffect, useRef } from "react";

export default function StreamingViewer({ ws, onStreamActive }) {
  const videoRef = useRef(null);
  const pcRef = useRef(null);
  const streamActiveRef = useRef(false);

  useEffect(() => {
    if (!ws) return;

    let disposed = false;

    const updateStreamActive = (next) => {
      if (streamActiveRef.current === next) return;
      streamActiveRef.current = next;
      if (onStreamActive) onStreamActive(next);
    };

    const start = () => {
      if (disposed) return;
      if (pcRef.current) return;

      const pc = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
      });
      pcRef.current = pc;

      pc.onconnectionstatechange = () => {
        console.log("[WebRTC] connectionState:", pc.connectionState);
        if (["failed", "disconnected", "closed"].includes(pc.connectionState)) {
          updateStreamActive(false);
        }
      };

      pc.onicecandidate = (event) => {
        if (event.candidate && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "candidate", candidate: event.candidate }));
        }
      };

      pc.ontrack = (event) => {
        const video = videoRef.current;
        if (!video) return;
        if (video.srcObject !== event.streams[0]) {
          video.srcObject = event.streams[0];
        }
        updateStreamActive(true);
      };
    };

    const onWsMessage = async (ev) => {
      if (!pcRef.current) return;

      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }

      const pc = pcRef.current;

      if (msg.type === "offer") {
        await pc.setRemoteDescription(msg.sdp);
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "answer", sdp: pc.localDescription }));
        }
      } else if (msg.type === "candidate") {
        try {
          await pc.addIceCandidate(msg.candidate);
        } catch {}
      }
    };

    const onWsOpen = () => start();

    ws.addEventListener("message", onWsMessage);
    ws.addEventListener("open", onWsOpen);

    if (ws.readyState === WebSocket.OPEN) start();

    return () => {
      disposed = true;
      ws.removeEventListener("message", onWsMessage);
      ws.removeEventListener("open", onWsOpen);

      if (pcRef.current) {
        pcRef.current.close();
        pcRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      updateStreamActive(false);
    };
  }, [ws, onStreamActive]);

  return <video ref={videoRef} className="camera-video" autoPlay playsInline muted />;
}
