import { useMemo, useState } from "react";
import MainLayout from "./MainLayout";
import GooeyText from "./GooeyText";

const VIEW = {
  LOGIN: "login",
  LOOKUP: "lookup",
};

const normalizeApiBase = (value) => (value ?? "").replace(/\/+$/g, "");
const API_IOT_BASE_URL = normalizeApiBase(import.meta.env.VITE_API_IOT_BASE_URL);
const USE_MOCK = String(import.meta.env.VITE_USE_MOCK).toLowerCase() === "true";

const mockReports = import.meta.glob("../mocks/*.json", { eager: true });
const mockSessions = import.meta.glob("../mocks/sessions/*.json", { eager: true });

const getMockReportById = (sequenceId, patientId) => {
  if (!sequenceId || !patientId) return null;
  const key = `../mocks/${sequenceId}_${patientId}.json`;
  return mockReports[key]?.default ?? null;
};

const getLatestMockReportForPatient = (patientId) => {
  if (!patientId) return null;
  const entries = Object.entries(mockReports)
    .filter(([path]) => path.endsWith(`_${patientId}.json`))
    .map(([path, module]) => {
      const file = path.split("/").pop() ?? "";
      const seq = Number(file.split("_")[0]);
      return Number.isNaN(seq) ? null : { sequenceId: seq, report: module?.default ?? null };
    })
    .filter(Boolean);
  if (entries.length === 0) return null;
  entries.sort((a, b) => b.sequenceId - a.sequenceId);
  return entries[0];
};

const getMockSessionById = (sessionId) => {
  if (!sessionId) return null;
  const key = `../mocks/sessions/${sessionId}.json`;
  return mockSessions[key]?.default ?? null;
};

const fetchSequenceReport = async (sequenceId, patientId) => {
  if (!sequenceId || !patientId) return null;
  const res = await fetch(
    `${API_IOT_BASE_URL}/api/patients/sequences/${sequenceId}`,
    { method: "GET" }
  );
  if (!res.ok) throw new Error("시퀀스 리포트를 불러오지 못했습니다.");
  const payload = await res.json();
  return payload?.data ?? null;
};

const formatDateTime = (value) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const calcAge = (birthDate) => {
  if (!birthDate) return null;
  const birth = new Date(birthDate);
  if (Number.isNaN(birth.getTime())) return null;
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age;
};

const formatPercent = (value) => {
  if (typeof value !== "number") return "-";
  return `${Math.round(value)}%`;
};

const formatNumber = (value, digits = 0) => {
  if (typeof value !== "number") return "-";
  return value.toFixed(digits);
};

const getSummaryTagClass = (tag) => {
  switch (tag) {
    case "STABLE":
      return "badge badge--stable";
    case "VARIABLE":
      return "badge badge--variable";
    case "UNSTABLE":
      return "badge badge--unstable";
    default:
      return "badge";
  }
};

const getTrendClass = (trend) => {
  switch (trend) {
    case "IMPROVING":
      return "badge badge--trend badge--improving";
    case "DECLINING":
      return "badge badge--trend badge--declining";
    case "STABLE":
      return "badge badge--trend badge--steady";
    default:
      return "badge badge--trend";
  }
};

const getTrendSymbol = (trend) => {
  switch (trend) {
    case "IMPROVING":
      return "▲";
    case "DECLINING":
      return "▼";
    case "STABLE":
      return "＝";
    default:
      return "•";
  }
};

const getSummaryTagDescription = (tag) => {
  switch (tag) {
    case "STABLE":
      return "주요/보조 관절 모두 일관적으로 수행되었습니다.";
    case "VARIABLE":
      return "주요 과제는 가능하나 안정성 변동이 관찰됩니다.";
    case "UNSTABLE":
      return "수행 자체 또는 안전성에 반복적 문제가 있습니다.";
    default:
      return "-";
  }
};

const getTrendDescription = (trend) => {
  switch (trend) {
    case "IMPROVING":
      return "세션 진행에 따라 수행이 개선됩니다.";
    case "STABLE":
      return "세션 내 큰 변화 없이 안정적으로 유지됩니다.";
    case "DECLINING":
      return "세션 후반으로 갈수록 수행이 저하됩니다.";
    default:
      return "-";
  }
};

export default function TherapistUI() {
  const [view, setView] = useState(VIEW.LOGIN);
  const [therapistId, setTherapistId] = useState("");
  const [therapistName, setTherapistName] = useState("");
  const [patients, setPatients] = useState([]);
  const [searchValue, setSearchValue] = useState("");
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [expandedExercise, setExpandedExercise] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");
  const [sessionDetails, setSessionDetails] = useState({});
  const [sessionLoading, setSessionLoading] = useState({});
  const [reportData, setReportData] = useState({
    profile: null,
    sequences: [],
    reportInput: null,
  });

  const visiblePatients = useMemo(() => {
    const trimmed = searchValue.trim();
    if (!trimmed) return [];
    return patients.filter((patient) => {
      const idMatch = String(patient.patientId).includes(trimmed);
      const nameMatch = patient.name?.includes(trimmed);
      return idMatch || nameMatch;
    });
  }, [searchValue, patients]);

  const handleTherapistLogin = async () => {
    const trimmedId = therapistId.trim();
    if (!trimmedId) return;
    setIsLoading(true);
    setErrorMessage("");
    try {
      if (USE_MOCK) {
        const data = {
          therapistId: Number(trimmedId) || 1,
          therapistName: "플러스",
          patients: [
            {
              patientId: 103,
              name: "박재활",
              gender: "MALE",
              age: 37,
              diseaseName: "뇌졸중",
            },
            {
              patientId: 105,
              name: "정이원",
              gender: "FEMALE",
              age: 45,
              diseaseName: "척수 손상",
            },
            {
              patientId: 120,
              name: "김미수",
              gender: "MALE",
              age: 62,
              diseaseName: "퇴행성 관절염",
            },
          ],
        };
        setTherapistName(data.therapistName ?? "");
        setPatients(Array.isArray(data.patients) ? data.patients : []);
        setSelectedPatient(null);
        setSearchValue("");
        setView(VIEW.LOOKUP);
        return;
      }
      const res = await fetch(`${API_IOT_BASE_URL}/api/therapist/${trimmedId}/dashboard`, {
        method: "GET",
      });
      if (!res.ok) {
        throw new Error("조회에 실패했습니다.");
      }
      const payload = await res.json();
      const data = payload?.data;
      setTherapistName(data?.therapistName ?? "");
      setPatients(Array.isArray(data?.patients) ? data.patients : []);
      setSelectedPatient(null);
      setSearchValue("");
      setView(VIEW.LOOKUP);
    } catch (err) {
      setErrorMessage("의료인 번호를 확인해주세요.");
    } finally {
      setIsLoading(false);
    }
  };

  const loadSessionDetail = async (sessionId) => {
    if (!sessionId || sessionLoading[sessionId] || sessionDetails[sessionId]) return;
    setSessionLoading((prev) => ({ ...prev, [sessionId]: true }));
    try {
      if (USE_MOCK) {
        const mock = getMockSessionById(sessionId);
        setSessionDetails((prev) => ({ ...prev, [sessionId]: mock?.data ?? null }));
        return;
      }
      const res = await fetch(`${API_IOT_BASE_URL}/api/patients/sessions/${sessionId}`, {
        method: "GET",
      });
      if (!res.ok) throw new Error("세션 상세를 불러오지 못했습니다.");
      const payload = await res.json();
      setSessionDetails((prev) => ({ ...prev, [sessionId]: payload?.data ?? null }));
    } catch (err) {
      setSessionDetails((prev) => ({ ...prev, [sessionId]: null }));
    } finally {
      setSessionLoading((prev) => ({ ...prev, [sessionId]: false }));
    }
  };

  const loadReport = async (patient) => {
    if (!patient) return;
    setReportLoading(true);
    setReportError("");
    setExpandedExercise(null);
    try {
      if (USE_MOCK) {
        const latestMock = getLatestMockReportForPatient(patient.patientId);
        const mockSequenceId = latestMock?.sequenceId ?? null;
        const mockReport = mockSequenceId
          ? getMockReportById(mockSequenceId, patient.patientId)
          : null;
        const mockSequences = mockSequenceId
          ? [
              {
                sequence_id: mockSequenceId,
                started_at: mockReport?.date ?? null,
                ended_at: mockReport?.date ?? null,
                feedback: "",
              },
            ]
          : [];

        setReportData({
          profile: {
            patient_id: patient.patientId,
            name: patient.name,
            birth_date: "1988-05-20",
            gender: patient.gender,
            disease_name: patient.diseaseName,
            rehab_phase: patient.rehabPhase ?? "MIDDLE",
            created_at: "2026-01-15T10:00:00",
          },
          sequences: mockSequences,
          reportInput: mockReport,
        });
        return;
      }

      const [profileRes, sequencesRes, reportRes] = await Promise.all([
        fetch(`${API_IOT_BASE_URL}/api/patients/${patient.patientId}`, { method: "GET" }),
        fetch(`${API_IOT_BASE_URL}/api/patients/${patient.patientId}/sequences`, {
          method: "GET",
        }),
        fetch(`${API_IOT_BASE_URL}/api/therapist/patient/${patient.patientId}/report`, {
          method: "GET",
        }),
      ]);

      if (!profileRes.ok) throw new Error("환자 정보를 불러오지 못했습니다.");

      const profilePayload = await profileRes.json();
      const sequencesPayload = sequencesRes.ok ? await sequencesRes.json() : { data: [] };
      const reportPayload = reportRes.ok ? await reportRes.json() : { data: null };
      const sequences = Array.isArray(sequencesPayload?.data) ? sequencesPayload.data : [];

      const latestSequence = sequences
        .slice()
        .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())[0];

      const reportInput =
        reportPayload?.data ??
        (latestSequence?.sequence_id
          ? await fetchSequenceReport(latestSequence.sequence_id, patient.patientId)
          : null);

      setReportData({
        profile: profilePayload?.data ?? null,
        sequences,
        reportInput,
      });
    } catch (err) {
      setReportError("리포트를 불러오지 못했습니다.");
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <MainLayout
      stageLabel="의료진 조회"
      nurseId={therapistId}
      hideCamera
      variant="therapist"
    >
      {view === VIEW.LOGIN && (
        <div className="placeholder-screen therapist-screen enter">
          <div className="screen-label">의료진 로그인</div>
          <h1>담당 확인</h1>
          <p className="lead">담당 의료인 번호를 입력해주세요.</p>
          <div className="therapist-login-layout">
            <div className="therapist-login">
              <label className="therapist-label" htmlFor="therapistId">
                의료인 번호
              </label>
              <input
                id="therapistId"
                className="therapist-input"
                type="text"
                placeholder="예시: 8451"
                value={therapistId}
                onChange={(event) => setTherapistId(event.target.value)}
              />
              <button
                className="therapist-primary"
                type="button"
                onClick={handleTherapistLogin}
                disabled={!therapistId.trim() || isLoading}
              >
                {isLoading ? "불러오는 중" : "로그인"}
              </button>
              {errorMessage && <div className="login-error">{errorMessage}</div>}
            </div>
            <div className="therapist-gooey">
              <GooeyText
                texts={["Rehab", "Insight", "Care", "Support", "Progress", "Empathy"]}
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
            <div className="therapist-header-left">
              <span className="screen-label">
                {therapistName ? `${therapistName} 담당 환자 조회` : "담당 환자 조회"}
              </span>
              <button
                className="therapist-ghost"
                type="button"
                onClick={() => {
                  setView(VIEW.LOGIN);
                  setSearchValue("");
                  setSelectedPatient(null);
                  setPatients([]);
                  setTherapistName("");
                  setReportData({
                    profile: null,
                    sequences: [],
                    reportInput: null,
                  });
                  setReportError("");
                }}
              >
                로그아웃
              </button>
            </div>
          </div>
          <div className="therapist-layout">
            <section className="therapist-left">
              <h1>환자 번호 입력</h1>
              <div className="therapist-search">
                <input
                  className="therapist-search-input"
                  type="text"
                  placeholder="환자 번호 또는 이름을 입력하세요."
                  value={searchValue}
                  onChange={(event) => setSearchValue(event.target.value)}
                />
              </div>
              <div className="therapist-results">
                {!searchValue.trim() && (
                  <div className="therapist-empty">
                    환자 번호를 입력하면 목록이 표시됩니다.
                  </div>
                )}
                {searchValue.trim() &&
                  (visiblePatients.length > 0 ? (
                    visiblePatients.map((patient) => (
                      <button
                        key={patient.patientId}
                        type="button"
                        className={`therapist-card${
                          selectedPatient?.patientId === patient.patientId ? " selected" : ""
                        }`}
                        onClick={() => {
                          setSelectedPatient(patient);
                          loadReport(patient);
                        }}
                      >
                        <div className="therapist-card-id">{patient.patientId}</div>
                        <div className="therapist-card-name">{patient.name}</div>
                        <div className="therapist-card-note">
                          병명: {patient.diseaseName}
                          <br />
                          성별: {patient.gender === "MALE" ? "남" : "여"}
                          <br />
                          나이: {patient.age}세
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="therapist-empty">일치하는 환자가 없습니다.</div>
                  ))}
              </div>
            </section>
            <section className="therapist-right">
              <div className="therapist-report">
                {reportLoading && (
                  <div className="therapist-empty">리포트를 불러오는 중입니다.</div>
                )}
                {!reportLoading && reportError && (
                  <div className="therapist-empty">{reportError}</div>
                )}
                {!reportLoading && !reportError && selectedPatient && (
                  <>
                    <div className="report-card">
                      <div className="report-card-title">환자 정보</div>
                      <div className="report-card-body">
                        {reportData.profile ? (
                          <>
                            {reportData.profile.name ?? reportData.reportInput?.patientName ?? "-"}{" "}
                            (ID {reportData.profile.patient_id}) |{" "}
                            {reportData.profile.gender === "MALE" ? "M" : "F"} |{" "}
                            {calcAge(reportData.profile.birth_date) ?? "-"}세
                            <br />
                            질환: {reportData.profile.disease_name} | 재활 단계:{" "}
                            {reportData.reportInput?.rehabPhase ??
                              reportData.profile.rehab_phase ??
                              "-"}{" "}
                            | 대상측: {reportData.reportInput?.side ?? "-"}
                          </>
                        ) : (
                          "환자 정보를 불러오지 못했습니다."
                        )}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title-row">
                        <div className="report-card-title">시퀀스 요약</div>
                        {reportData.reportInput && (
                          <div className="summary-meta summary-meta-inline">
                            <span>Seq #{reportData.reportInput.sequenceId}</span> |{" "}
                            <span>
                              운동 개수:{" "}
                              {reportData.reportInput.overallSummary?.totalExercises ?? "-"}
                            </span>{" "}
                            |{" "}
                            <span>기록일 {formatDateTime(reportData.reportInput.date)}</span>
                          </div>
                        )}
                      </div>
                      <div className="report-card-body">
                        {reportData.reportInput ? (
                          <>
                            <div className="summary-headline">
                              {reportData.reportInput.overallSummary?.title ?? "-"}
                            </div>
                            <div className="summary-body">
                              {reportData.reportInput.overallSummary?.overallAssessment ?? "-"}
                            </div>
                          </>
                        ) : (
                          "시퀀스 요약 정보가 없습니다."
                        )}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">주요 위험 신호</div>
                      <div className="report-card-body">
                        {reportData.reportInput?.riskSignals?.length ? (
                          <ul className="report-bullets report-bullets--risk">
                            {reportData.reportInput.riskSignals.map((item, index) => (
                              <li key={`risk-${index}`}>{item}</li>
                            ))}
                          </ul>
                        ) : (
                          <div className="report-empty">위험 신호가 없습니다.</div>
                        )}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">다음 재활 집중 포인트</div>
                      <div className="report-card-body">
                        {reportData.reportInput?.nextFocus?.length ? (
                          <ul className="report-bullets report-bullets--focus">
                            {reportData.reportInput.nextFocus.map((item, index) => (
                              <li key={`focus-${index}`}>{item}</li>
                            ))}
                          </ul>
                        ) : (
                          <div className="report-empty">집중 포인트가 없습니다.</div>
                        )}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">세션 상세 정보</div>
                      <div className="report-card-body">
                        {reportData.reportInput?.exerciseSummaries?.length ? (
                          <div className="exercise-list">
                            {reportData.reportInput.exerciseSummaries.map((exercise, index) => {
                              const key = `${exercise.exerciseName ?? "exercise"}-${index}`;
                              const isOpen = expandedExercise === key;
                              return (
                                <div key={key} className="exercise-card">
                                  <button
                                    type="button"
                                    className={`exercise-header${isOpen ? " open" : ""}`}
                                    onClick={() => {
                                      const nextOpen = isOpen ? null : key;
                                      setExpandedExercise(nextOpen);
                                      if (!isOpen && exercise.sessionId) {
                                        loadSessionDetail(exercise.sessionId);
                                      }
                                    }}
                                    aria-expanded={isOpen}
                                  >
                                    <div className="exercise-title">
                                      <span>{exercise.exerciseName ?? "-"}</span>
                                      <span className={getSummaryTagClass(exercise.summaryTag)}>
                                        {exercise.summaryTag ?? "-"}
                                      </span>
                                      <span className={getTrendClass(exercise.withinSessionTrend)}>
                                        {getTrendSymbol(exercise.withinSessionTrend)}{" "}
                                        {exercise.withinSessionTrend ?? "-"}
                                      </span>
                                    </div>
                                    <div className="exercise-meta">
                                      <span className="meta-pill-compact">
                                        성공 비율 {formatPercent(exercise.performance?.successRate)}
                                      </span>
                                      <span className="meta-pill-compact">
                                        평균 점수 {formatNumber(exercise.performance?.averageScore)}
                                      </span>
                                      <span className="exercise-toggle">{isOpen ? "닫기" : "보기"}</span>
                                    </div>
                                  </button>
                                  {isOpen && (
                                    <div className="exercise-body">
                                      <div className="exercise-note">
                                        {exercise.sessionNote ?? "-"}
                                      </div>
                                      <div className="session-mini-charts">
                                        {(() => {
                                          const sessionId = exercise.sessionId;
                                          const session = sessionId ? sessionDetails[sessionId] : null;
                                          const tries = session?.tries ?? [];
                                          const total = session?.total_tries ?? tries.length;
                                          const success =
                                            session?.success_tries ??
                                            tries.filter((t) => t.result === "SUCCESS").length;
                                          const successRate = total
                                            ? Math.round((success / total) * 100)
                                            : 0;
                                          const sensorValues = tries
                                            .map((t) => Number(t.goal_sensor))
                                            .filter((v) => Number.isFinite(v));
                                          const maxVal = sensorValues.length
                                            ? Math.max(...sensorValues)
                                            : 0;
                                          const failReasons = tries
                                            .filter((t) => t.result === "FAIL" && t.fail_name)
                                            .reduce((acc, t) => {
                                              acc[t.fail_name] = (acc[t.fail_name] || 0) + 1;
                                              return acc;
                                            }, {});
                                          const topFails = Object.entries(failReasons)
                                            .sort((a, b) => b[1] - a[1])
                                            .slice(0, 2);

                                          if (!sessionId) {
                                            return (
                                              <div className="session-empty">
                                                세션 상세 데이터가 없습니다.
                                              </div>
                                            );
                                          }
                                          if (sessionLoading[sessionId]) {
                                            return (
                                              <div className="session-empty">
                                                세션 데이터를 불러오는 중입니다.
                                              </div>
                                            );
                                          }
                                          if (!session) {
                                            return (
                                              <div className="session-empty">
                                                세션 상세 데이터가 없습니다.
                                              </div>
                                            );
                                          }

                                          return (
                                            <>
                                              <div className="session-section-title">세션 개요</div>
                                              <div className="session-kpi">
                                                <span>
                                                  성공 {success}/{total}
                                                </span>
                                                <span>성공률 {successRate}%</span>
                                              </div>
                                              {topFails.length > 0 && (
                                                <div className="session-fails">
                                                  실패 사유:{" "}
                                                  {topFails
                                                    .map(([name, count]) => `${name} (${count})`)
                                                    .join(", ")}
                                                </div>
                                              )}
                                              {sensorValues.length > 0 && (
                                                <>
                                                  <div className="session-trend">
                                                    <div className="session-scale">
                                                      <span>100</span>
                                                      <span>50</span>
                                                      <span>0</span>
                                                    </div>
                                                    {(() => {
                                                      const points = sensorValues.map((val, i) => {
                                                        const x =
                                                          sensorValues.length === 1
                                                            ? 50
                                                            : (i / (sensorValues.length - 1)) * 100;
                                                        const y = 100 - (maxVal ? (val / maxVal) * 100 : 0);
                                                        return { x, y };
                                                      });
                                                      const pointsStr = points
                                                        .map((p) => `${p.x},${p.y}`)
                                                        .join(" ");

                                                      return (
                                                        <svg
                                                          className="session-line"
                                                          viewBox="0 0 100 100"
                                                          preserveAspectRatio="none"
                                                        >
                                                          <polyline
                                                            className="session-line-stroke"
                                                            points={pointsStr}
                                                          />
                                                        </svg>
                                                      );
                                                    })()}
                                                  </div>
                                                </>
                                              )}
                                              {tries.length > 0 && (
                                                <>
                                                  <div className="session-section-title">
                                                    Try 결과 흐름
                                                  </div>
                                                  <div className="session-timeline">
                                                    {tries.map((t, i) => (
                                                      <span
                                                        key={`result-${i}`}
                                                        className={`session-dot ${
                                                          t.result === "SUCCESS" ? "success" : "fail"
                                                        }`}
                                                        title={
                                                          t.result === "FAIL"
                                                            ? t.fail_name ?? "FAIL"
                                                            : "SUCCESS"
                                                        }
                                                      />
                                                    ))}
                                                  </div>
                                                  <div className="session-legend">
                                                    <span>
                                                      <span className="session-dot success" />
                                                      성공
                                                    </span>
                                                    <span>
                                                      <span className="session-dot fail" />
                                                      실패
                                                    </span>
                                                  </div>
                                                </>
                                              )}
                                            </>
                                          );
                                        })()}
                                      </div>

                                      <div className="exercise-tags-explain">
                                        <div className="exercise-tag-row">
                                          <span className="exercise-tag-label">세션 요약:</span>
                                          <span className={getSummaryTagClass(exercise.summaryTag)}>
                                            {exercise.summaryTag ?? "-"}
                                          </span>
                                          <span className="exercise-tag-desc">
                                            {getSummaryTagDescription(exercise.summaryTag)}
                                          </span>
                                        </div>
                                        <div className="exercise-tag-row">
                                          <span className="exercise-tag-label">세션 경향:</span>
                                          <span className={getTrendClass(exercise.withinSessionTrend)}>
                                            {getTrendSymbol(exercise.withinSessionTrend)}{" "}
                                            {exercise.withinSessionTrend ?? "-"}
                                          </span>
                                          <span className="exercise-tag-desc">
                                            {getTrendDescription(exercise.withinSessionTrend)}
                                          </span>
                                        </div>
                                      </div>
                                      {exercise.keyObservations?.length ? (
                                        <ul className="exercise-list-items">
                                          {exercise.keyObservations.map((note, noteIndex) => (
                                            <li key={`${key}-note-${noteIndex}`}>{note}</li>
                                          ))}
                                        </ul>
                                      ) : (
                                        <div className="exercise-muted">
                                          주요 관찰 내용이 없습니다.
                                        </div>
                                      )}
                                      <div className="exercise-compare">
                                        <strong>이전 세션과 비교: </strong>
                                        {exercise.comparisonToPrevious?.used ? (
                                          <>
                                            <span
                                              className={getTrendClass(
                                                exercise.comparisonToPrevious.trend
                                              )}
                                            >
                                              {getTrendSymbol(exercise.comparisonToPrevious.trend)}{" "}
                                              {exercise.comparisonToPrevious.trend ?? "-"}
                                            </span>
                                            <span className="exercise-compare-text">
                                              {exercise.comparisonToPrevious.trendDescription ?? "-"}
                                            </span>
                                          </>
                                        ) : (
                                          <span className="tag tag--muted">
                                            이전 세션과 비교 데이터가 없습니다.
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          "운동 요약 정보가 없습니다."
                        )}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">최근 시퀀스</div>
                      <div className="report-list">
                        {reportData.sequences.length > 0 ? (
                          reportData.sequences.slice(0, 5).map((item) => (
                            <div key={item.sequence_id} className="report-list-row">
                              <span className="report-date">
                                {formatDateTime(item.started_at)} ~ {formatDateTime(item.ended_at)}
                              </span>
                              <span className="report-feedback">{item.feedback || "-"}</span>
                            </div>
                          ))
                        ) : (
                          <div className="therapist-empty">최근 시퀀스 기록이 없습니다.</div>
                        )}
                      </div>
                    </div>
                  </>
                )}
                {!reportLoading && !reportError && !selectedPatient && (
                  <div className="therapist-empty">
                    환자를 선택하면 리포트가 표시됩니다.
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
