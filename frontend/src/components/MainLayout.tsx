import { useEffect, useRef, useState, type ReactNode } from "react";
import StreamingViewer from "./StreamingViewer";

type MainLayoutProps = {
  children: ReactNode;
  stageLabel?: string;
  patientId?: string;
  nurseId?: string;
  stageIndex?: number | null;
  stageTotal?: number;
  hideCamera?: boolean;
  variant?: "patient" | "therapist";
  cameraNotice?: string;
};

export default function MainLayout({
  children,
  stageLabel,
  patientId,
  nurseId,
  stageIndex,
  stageTotal = 5,
  hideCamera = false,
  variant = "patient",
  cameraNotice,
}: MainLayoutProps) {
  const patientLabel = patientId ? `환자 번호: ${patientId}` : "환자 번호: 미확인";
  const nurseLabel = nurseId ? `의료인 번호: ${nurseId}` : "의료인 번호: 미확인";
  const stageProgress =
    stageIndex && stageTotal ? `${stageIndex}/${stageTotal} 단계` : null;

  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const WS_URL = "/test/ws";

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WS connected");
      setConnected(true);
      ws.send(JSON.stringify({ type: "ready" }));
    };

    ws.onclose = () => {
      console.log("WS closed");
      setConnected(false);
    };

    ws.onerror = (e) => console.error("WS error", e);
    ws.onmessage = (e) => console.log("WS message:", e.data);

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, []);

  return (
    <div className={`app-shell${variant === "therapist" ? " therapist-shell" : ""}`}>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" />
          <span className="brand-name">행가래</span>
        </div>

        <div className="header-meta">
          <div className="meta-pill">{patientLabel}</div>
          <div className="meta-pill">{nurseLabel}</div>
          {stageProgress && <div className="meta-pill">{stageProgress}</div>}
          <div className="meta-pill accent">{stageLabel}</div>

          {/* 추가: WS 연결 상태 표시 */}
          <div className={`meta-pill ${connected ? "accent" : ""}`}>
            {connected ? "WS 연결됨" : "WS 끊김"}
          </div>
        </div>
      </header>

      <div className={`layout-body${hideCamera ? " layout-body-wide" : ""}`}>
        {!hideCamera && (
          <section className="camera-panel">
            <div className="panel-row">
              <div className="panel-header">실시간 카메라</div>

              <button
                className="signal-restart"
                type="button"
                onClick={() => {
                  const ok = window.confirm(
                    "재활 운동 보조를 재시작 합니다. 계속할까요?"
                  );
                  if (!ok) return;

                  const ws = wsRef.current;
                  if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: "run" }));
                  } else {
                    console.warn("WebSocket not connected");
                  }

                  // window.dispatchEvent(new Event("webrtc-restart"));
                }}
              />
            </div>

            <div className="camera-feed">
              <StreamingViewer />
              <div className="camera-overlay">
                <span className="overlay-dot" />
                <span className="overlay-ring" />
              </div>
              <div className="pose-silhouette" />
              <div className="target-frame">
                <span />
                <span />
                <span />
                <span />
              </div>
            </div>

            {cameraNotice && <div className="camera-notice">{cameraNotice}</div>}
            <div className="panel-footer">자세 인식 영역 · 목표 위치 표시</div>
          </section>
        )}

        <section className="right-panel">{children}</section>
      </div>
    </div>
  );
}
