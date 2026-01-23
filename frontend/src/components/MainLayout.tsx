import type { ReactNode } from "react";

type MainLayoutProps = {
  children: ReactNode;
  stageLabel?: string;
  patientId?: string;
  nurseId?: string;
  stageIndex?: number | null;
  stageTotal?: number;
  hideCamera?: boolean;
  variant?: "patient" | "therapist";
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
}: MainLayoutProps) {
  const patientLabel = patientId ? `환자 번호: ${patientId}` : "환자 번호: 미확인";
  const nurseLabel = nurseId ? `의료인 번호: ${nurseId}` : "의료인 번호: 미확인";
  const stageProgress =
    stageIndex && stageTotal ? `${stageIndex}/${stageTotal} 단계` : null;

  return (
    <div className={`app-shell${variant === "therapist" ? " therapist-shell" : ""}`}>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" />
          <span className="brand-name">행가래</span>
        </div>
        <div className="header-meta">
          <div className="meta-pill">{nurseLabel}</div>
          {stageProgress && <div className="meta-pill">{stageProgress}</div>}
          <div className="meta-pill accent">{stageLabel}</div>
        </div>
      </header>
      <div className={`layout-body${hideCamera ? " layout-body-wide" : ""}`}>
        {!hideCamera && (
          <section className="camera-panel">
            <div className="panel-header">실시간 카메라</div>
            <div className="camera-feed">
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
            <div className="panel-footer">
              자세 인식 영역 · 목표 위치 표시
            </div>
          </section>
        )}
        <section className="right-panel">{children}</section>
      </div>
    </div>
  );
}
