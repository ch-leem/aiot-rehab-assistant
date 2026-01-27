import { FadeText } from "./ui/fade-text";

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
  const goalLines = (() => {
    const hasUpper = exerciseIds.includes(1);
    const hasLower = exerciseIds.includes(2);
    const total = (hasUpper ? 1 : 0) + (hasLower ? 1 : 0);
    if (total === 0) return ["오늘 운동 없음"];
    const lines: string[] = [];
    if (hasUpper) lines.push("상체 1세트");
    if (hasLower) lines.push("하체 1세트");
    lines.push(`총 ${total}세트`);
    return lines;
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
            <div className="card-title info-title">환자 정보</div>
            <div className="card-meta info-list">
              <div className="info-line">
                <span className="info-label">환자 번호</span>
                <FadeText
                  wrapperClassName="fade-text-wrapper"
                  className="info-value"
                  direction="up"
                  framerProps={{ show: { transition: { delay: 0.1, duration: 1.4 } } }}
                  text={patientId || "-"}
                />
              </div>
              <div className="info-line">
                <span className="info-label">이름</span>
                <FadeText
                  wrapperClassName="fade-text-wrapper"
                  className="info-value"
                  direction="up"
                  framerProps={{ show: { transition: { delay: 0.2, duration: 1.4 } } }}
                  text={nameLabel}
                />
              </div>
              <div className="info-line">
                <span className="info-label">질환 정보</span>
                <FadeText
                  wrapperClassName="fade-text-wrapper"
                  className="info-value"
                  direction="up"
                  framerProps={{ show: { transition: { delay: 0.3, duration: 1.4 } } }}
                  text={diseaseLabel}
                />
              </div>
              <div className="info-line">
                <span className="info-label">중증 단계</span>
                <FadeText
                  wrapperClassName="fade-text-wrapper"
                  className="info-value"
                  direction="up"
                  framerProps={{ show: { transition: { delay: 0.4, duration: 1.4 } } }}
                  text={phaseLabel}
                />
              </div>
            </div>
          </div>
          <span className="id-badge">확인 필요</span>
        </div>
        <div className="info-card highlight goal-card">
          <div className="card-title goal-title">오늘 목표</div>
          <div className="card-meta goal-list">
            {goalLines.map((line, index) => (
              <div
                key={line}
                className={`goal-line${line.startsWith("총") ? " total" : ""}`}
              >
                <FadeText
                  wrapperClassName="fade-text-wrapper goal-text-wrapper"
                  className="goal-line-text"
                  direction="left"
                  framerProps={{
                    show: { transition: { delay: 0.3 * (index + 1), duration: 2.2 } },
                  }}
                  text={line}
                />
              </div>
            ))}
          </div>
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
