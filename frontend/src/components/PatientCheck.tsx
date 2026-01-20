type PatientCheckProps = {
  onStart: () => void;
  onBack: () => void;
};

export default function PatientCheck({ onStart, onBack }: PatientCheckProps) {
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
            <div className="card-title">환자 번호 1203</div>
            <div className="card-meta">
              <span className="name-text">김민수 님</span> · 좌측 편마비 · 4주차
            </div>
          </div>
          <span className="id-badge">확인 필요</span>
        </div>
        <div className="info-card accent">
          <div className="card-title">오늘 목표</div>
          <div className="card-meta">상체 동작 3세트 완료</div>
        </div>
      </div>
      <div className="notice">
        카메라 화면에 팔과 어깨가 모두 보이도록 앉아주세요.
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
