import { useEffect, useRef } from "react";

export default function StreamingViewer({ wsUrl = "wss://70.12.246.185:18080/ws" }) {
  const videoRef = useRef(null);
  const pcRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    const start = async () => {
      if (!mounted || pcRef.current || wsRef.current) return;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        const pc = new RTCPeerConnection({
          iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });
        pcRef.current = pc;

        pc.ondatachannel = (ev) => {
          const ch = ev.channel;
          ch.onmessage = (e) => {
            let o = null;
            try {
              o = JSON.parse(e.data);
            } catch {
              return;
            }
            if (!o) return;
            if (o.type === "frame_meta") {
              ch.send(
                JSON.stringify({
                  type: "echo",
                  frame_idx: o.frame_idx,
                  tx_ms: o.tx_ms,
                  rx_ms: performance.now(),
                })
              );
            }
          };
        };

        pc.ontrack = (event) => {
          const video = videoRef.current;
          if (!video) return;
          if (video.srcObject !== event.streams[0]) {
            video.srcObject = event.streams[0];
          }
        };

        pc.onicecandidate = (event) => {
          if (event.candidate) {
            ws.send(JSON.stringify({ type: "candidate", candidate: event.candidate }));
          }
        };

        ws.send(JSON.stringify({ type: "ready" }));
      };

      ws.onmessage = async (ev) => {
        const msg = JSON.parse(ev.data);
        if (!pcRef.current) return;

        if (msg.type === "offer") {
          await pcRef.current.setRemoteDescription(msg.sdp);
          const answer = await pcRef.current.createAnswer();
          await pcRef.current.setLocalDescription(answer);
          ws.send(JSON.stringify({ type: "answer", sdp: pcRef.current.localDescription }));
        } else if (msg.type === "candidate") {
          try {
            await pcRef.current.addIceCandidate(msg.candidate);
          } catch {
            // ignore candidate errors
          }
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
      };
    };

    start();

    return () => {
      mounted = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (pcRef.current) {
        pcRef.current.close();
        pcRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [wsUrl]);

  return <video ref={videoRef} className="camera-video" autoPlay playsInline muted />;
}
