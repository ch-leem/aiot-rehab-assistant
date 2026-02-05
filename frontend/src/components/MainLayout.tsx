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
  const [streamActive, setStreamActive] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const [wsState, setWsState] = useState<WebSocket | null>(null);
  const [confirmAction, setConfirmAction] = useState<"restart" | "stop" | null>(null);

  useEffect(() => {
    const WS_URL = "test/ws";

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    setWsState(ws);

    ws.onopen = () => {
      console.log("WS connected");
      setConnected(true);
      ws.send(JSON.stringify({ type: "ready" }));
    };

    ws.onclose = () => {
      console.log("WS closed");
      setConnected(false);
      setStreamActive(false);
      wsRef.current = null;
      setWsState(null);
    };

    ws.onerror = (e) => console.error("WS error", e);
    const onMsg = (e: MessageEvent) => console.log("WS message:", e.data);
    ws.addEventListener("message", onMsg);

    return () => {
      ws.removeEventListener("message", onMsg);
      ws.close();
      wsRef.current = null;
      setWsState(null);
    };

  }, []);

  const sendWsSignal = (type: "run" | "stop") => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type }));
    } else {
      console.warn("WebSocket not connected");
    }
  };

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
        </div>
      </header>

      <div className={`layout-body${hideCamera ? " layout-body-wide" : ""}`}>
        {!hideCamera && (
          <section className="camera-panel">
            <div className="panel-row">
              <div className="panel-header">
                실시간 카메라
                <div className="ws-pill">
                  <label className="ws-bubble">
                    <input
                      className="bubble"
                      type="checkbox"
                      checked={streamActive}
                      readOnly
                      disabled
                      aria-label={streamActive ? "WS 연결됨" : "WS 끊김"}
                    />
                  </label>
                </div>
              </div>

              <div className="panel-actions">
                <button
                  className="signal-restart action-icon"
                  type="button"
                  aria-label="카메라 재시작"
                  onClick={() => {
                    setConfirmAction("restart");
                  }}
                >
                  <span className="action-sheen" aria-hidden="true" />
                  <svg
                    className="action-icon-svg"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path d="M12 6V3L8 7l4 4V8c2.757 0 5 2.243 5 5a5 5 0 1 1-9.584-2H5.264A7 7 0 1 0 12 6z" />
                  </svg>
                </button>

                <button
                  className="signal-stop action-icon"
                  type="button"
                  aria-label="카메라 종료"
                  onClick={() => {
                    setConfirmAction("stop");
                  }}
                >
                  <span className="action-sheen" aria-hidden="true" />
                  <svg
                    className="action-icon-svg"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path d="M7 7h10v10H7z" />
                  </svg>
                </button>
              </div>

              </div>
              

            <div className="camera-feed">
              <StreamingViewer ws={wsState} onStreamActive={setStreamActive} />
              <div className="camera-overlay">
                <span className="overlay-dot" />
                <span className="overlay-ring" />
              </div>
              <div className="pose-silhouette" />
              {!connected && (
                <div className="target-frame">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
              )}
            </div>

            {cameraNotice && <div className="camera-notice">{cameraNotice}</div>}
            <div className="panel-footer">자세 인식 영역 · 목표 위치 표시</div>
          </section>
        )}

        <section className="right-panel">{children}</section>
      </div>

      {confirmAction && (
        <div className="alert-overlay" role="dialog" aria-modal="true">
          <div
            className={`alert-card ${
              confirmAction === "restart" ? "alert-warning" : "alert-error"
            }`}
          >
            <div className="alert-title">
              {confirmAction === "restart" ? "Warning" : "Error"}
            </div>
            <div className="alert-body">
              {confirmAction === "restart"
                ? "재활 운동 보조를 재시작 합니다. 계속할까요?"
                : "재활 운동 보조를 중지 합니다. 계속할까요?"}
            </div>
            <div className="alert-actions">
              <button
                type="button"
                className="alert-ghost"
                onClick={() => setConfirmAction(null)}
              >
                취소
              </button>
              <button
                type="button"
                className="alert-primary"
                onClick={() => {
                  const action = confirmAction;
                  setConfirmAction(null);
                  if (action === "restart") {
                    sendWsSignal("run");
                  } else if (action === "stop") {
                    sendWsSignal("stop");
                  }
                }}
              >
                {confirmAction === "restart" ? "재시작" : "종료"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
