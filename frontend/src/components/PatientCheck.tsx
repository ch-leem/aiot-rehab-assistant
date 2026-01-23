type PatientCheckProps = {
  onStart: () => void;
  onBack: () => void;
  patientId?: string;
  patientName?: string;
  diseaseName?: string;
  rehabPhase?: string;
  exerciseIds?: number[];
};

export default function PatientCheck({
  onStart,
  onBack,
  patientId,
  patientName,
  diseaseName,
  rehabPhase,
  exerciseIds = [],
}: PatientCheckProps) {
  const nameLabel = patientName ? `${patientName} 님` : "환자 님";
  const diseaseLabel = diseaseName || "-";
  const phaseLabel = rehabPhase || "-";
  const goalLabel = (() => {
    const hasUpper = exerciseIds.includes(1);
    const hasLower = exerciseIds.includes(2);
    const total = (hasUpper ? 1 : 0) + (hasLower ? 1 : 0);
    if (total === 0) return "오늘 운동 없음";
    const lines: string[] = [];
    if (hasLower) lines.push("하체 1단계");
    if (hasUpper) lines.push("상체 1단계");
    lines.push(`총 ${total}단계`);
    return lines.join(" · ");
  })();

  return (
    <div className="patient-check enter">
      <div className="screen-label">환자 확인</div>
      <h1>환자 확인</h1>
      <p className="lead">
        오늘도 집으로 가는 길에 한 걸음 더 가까워집니다.
      </p>
      <div className="info-grid">
        <div className="info-card highlight">
          <div>
            <div className="card-title">환자 정보</div>
            <div className="card-meta">
              <div>환자 번호 {patientId || "-"}</div>
              <div>이름 {nameLabel}</div>
              <div>질환 정보 {diseaseLabel}</div>
              <div>중증 단계 {phaseLabel}</div>
            </div>
          </div>
          <span className="id-badge">확인 필요</span>
        </div>
        <div className="info-card accent">
          <div className="card-title">오늘 목표</div>
          <div className="card-meta">{goalLabel}</div>
        </div>
      </div>
      <div className="cta-row">
        <button className="primary-button" type="button" onClick={onStart}>
          시작하기
        </button>
        <button className="ghost-button" type="button" onClick={onBack}>
          되돌아가기
        </button>
      </div>
    </div>
  );
}
