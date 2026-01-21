import { useMemo, useState } from "react";
import MainLayout from "./MainLayout";
import GooeyText from "./GooeyText";

const PATIENTS = [
  { id: "1203", name: "김민수", note: "좌측 편마비" },
  { id: "2201", name: "박지은", note: "어깨 가동 범위 감소" },
  { id: "1734", name: "최영수", note: "상지 근력 저하" },
  { id: "3012", name: "이수정", note: "균형 감각 저하" },
  { id: "1456", name: "정하늘", note: "견관절 통증" },
];

const REPORTS = {
  1203: {
    title: "최근 4회 경과 요약",
    summary:
      "상체 동작의 안정성이 좋아졌고, 일상 동작 속도가 균일해졌습니다.",
    highlight: "팔 내리기 동작에서 어깨 떨림이 감소했습니다.",
    next: "다음 회차는 호흡 유지와 팔 고정에 집중해주세요.",
    sessions: [
      { date: "2024.03.18", note: "호흡 안정, 자세 유지 양호" },
      { date: "2024.03.20", note: "팔 들기 범위 개선" },
      { date: "2024.03.22", note: "피로도 증가, 속도 유지 어려움" },
      { date: "2024.03.25", note: "동작 안정, 반복 정확도 상승" },
    ],
  },
  2201: {
    title: "최근 4회 경과 요약",
    summary: "어깨 가동 범위가 일정해졌고 좌우 이동이 부드러워졌습니다.",
    highlight: "좌측 어깨의 긴장이 줄어들었습니다.",
    next: "다음 회차는 통증 체크 후 강도를 조절해주세요.",
    sessions: [
      { date: "2024.03.17", note: "통증 호소, 속도 완화 필요" },
      { date: "2024.03.19", note: "범위 유지 안정" },
      { date: "2024.03.21", note: "좌우 이동 리듬 안정" },
      { date: "2024.03.24", note: "자세 이탈 감소" },
    ],
  },
  1734: {
    title: "최근 4회 경과 요약",
    summary: "상지 근력 유지가 꾸준하며 반복 동작 속도가 일정합니다.",
    highlight: "팔 들어 올리기 동작의 지연이 줄었습니다.",
    next: "다음 회차는 동작 시작 타이밍을 맞춰주세요.",
    sessions: [
      { date: "2024.03.16", note: "근력 유지, 피로도 낮음" },
      { date: "2024.03.19", note: "동작 시작 지연" },
      { date: "2024.03.22", note: "속도 개선" },
      { date: "2024.03.25", note: "안정적 유지" },
    ],
  },
  3012: {
    title: "최근 4회 경과 요약",
    summary: "균형 유지 시간이 길어지고 동작 종료 후 안정이 좋아졌습니다.",
    highlight: "체중 중심 이동이 부드럽게 연결됩니다.",
    next: "다음 회차는 균형 유지 시간을 2초 더 늘려주세요.",
    sessions: [
      { date: "2024.03.15", note: "균형 흔들림 있음" },
      { date: "2024.03.18", note: "중심 이동 개선" },
      { date: "2024.03.21", note: "균형 유지 시간 증가" },
      { date: "2024.03.24", note: "안정적 마무리" },
    ],
  },
  1456: {
    title: "최근 4회 경과 요약",
    summary: "견관절 통증이 줄어들고 동작 중 긴장이 완화되었습니다.",
    highlight: "팔 내리기에서 통증 표시가 감소했습니다.",
    next: "다음 회차는 스트레칭 시간을 조금 늘려주세요.",
    sessions: [
      { date: "2024.03.16", note: "통증 호소 있음" },
      { date: "2024.03.19", note: "통증 감소" },
      { date: "2024.03.22", note: "긴장 완화" },
      { date: "2024.03.25", note: "안정적 진행" },
    ],
  },
};

const VIEW = {
  LOGIN: "login",
  LOOKUP: "lookup",
};

export default function TherapistUI() {
  const [view, setView] = useState(VIEW.LOGIN);
  const [therapistId, setTherapistId] = useState("");
  const [searchValue, setSearchValue] = useState("");
  const [selectedPatient, setSelectedPatient] = useState(null);

  const visiblePatients = useMemo(() => {
    const trimmed = searchValue.trim();
    if (!trimmed) return [];
    return PATIENTS.filter((patient) => patient.id.includes(trimmed));
  }, [searchValue]);

  return (
    <MainLayout stageLabel="의료진 화면" nurseId={therapistId} hideCamera variant="therapist">
      {view === VIEW.LOGIN && (
        <div className="placeholder-screen therapist-screen enter">
          <div className="screen-label">의료진 로그인</div>
          <h1>담당 확인</h1>
          <p className="lead">
            의료인 번호를 입력하면 환자 조회 화면으로 이동합니다.
          </p>
          <div className="therapist-login-layout">
            <div className="therapist-login">
              <label className="therapist-label" htmlFor="therapistId">
                의료인 번호
              </label>
              <input
                id="therapistId"
                className="therapist-input"
                type="text"
                placeholder="예시"
                value={therapistId}
                onChange={(event) => setTherapistId(event.target.value)}
              />
              <button
                className="therapist-primary"
                type="button"
                onClick={() => setView(VIEW.LOOKUP)}
                disabled={!therapistId.trim()}
              >
                로그인
              </button>
            </div>
            <div className="therapist-gooey">
              <GooeyText
                texts={[
                  "정예진",
                  "신원호",
                  "김범석",
                  "한의표",
                  "이혜연",
                  "임찬혁",
                ]}
                morphTime={1.6}
                cooldownTime={0.55}
              />
            </div>
          </div>
        </div>
      )}
      {view === VIEW.LOOKUP && (
        <div className="placeholder-screen therapist-screen enter">
          <div className="therapist-header">
            <button
              className="therapist-ghost"
              type="button"
              onClick={() => {
                setView(VIEW.LOGIN);
                setSearchValue("");
                setSelectedPatient(null);
              }}
            >
              로그아웃
            </button>
            <div className="screen-label">환자 조회</div>
          </div>
          <div className="therapist-layout">
            <section className="therapist-left">
              <h1>환자 번호 입력</h1>
              <div className="therapist-search">
                <input
                  className="therapist-search-input"
                  type="text"
                  placeholder="환자 번호를 입력하세요"
                  value={searchValue}
                  onChange={(event) => setSearchValue(event.target.value)}
                />
              </div>
              <div className="therapist-results">
                {!searchValue.trim() && (
                  <div className="therapist-empty">
                    입력하면 아래에 환자 목록이 표시됩니다.
                  </div>
                )}
                {searchValue.trim() &&
                  (visiblePatients.length > 0 ? (
                    visiblePatients.map((patient) => (
                      <button
                        key={patient.id}
                        type="button"
                        className={`therapist-card${
                          selectedPatient?.id === patient.id ? " selected" : ""
                        }`}
                        onClick={() => setSelectedPatient(patient)}
                      >
                        <div className="therapist-card-id">{patient.id}</div>
                        <div className="therapist-card-name">{patient.name}</div>
                        <div className="therapist-card-note">{patient.note}</div>
                      </button>
                    ))
                  ) : (
                    <div className="therapist-empty">
                      일치하는 환자가 없습니다.
                    </div>
                  ))}
              </div>
            </section>
            <section className="therapist-right">
              <div className="therapist-report">
                {selectedPatient ? (
                  <>
                    <div className="report-header">
                      <div>
                        <div className="report-title">
                          {selectedPatient.name} 환자 리포트
                        </div>
                        <div className="report-sub">
                          환자 번호 {selectedPatient.id}
                        </div>
                      </div>
                      <span className="report-pill">임시 리포트</span>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">
                        {REPORTS[selectedPatient.id]?.title}
                      </div>
                      <div className="report-card-body">
                        {REPORTS[selectedPatient.id]?.summary}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">주요 관찰</div>
                      <div className="report-card-body">
                        {REPORTS[selectedPatient.id]?.highlight}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">다음 회차 제안</div>
                      <div className="report-card-body">
                        {REPORTS[selectedPatient.id]?.next}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">최근 세션 기록</div>
                      <div className="report-list">
                        {REPORTS[selectedPatient.id]?.sessions.map((item) => (
                          <div key={item.date} className="report-list-row">
                            <span>{item.date}</span>
                            <span>{item.note}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="therapist-empty">
                    환자 목록에서 선택하면 리포트가 표시됩니다.
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      )}
    </MainLayout>
  );
}
