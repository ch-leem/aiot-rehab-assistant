import { useMemo, useState } from "react";
import MainLayout from "./MainLayout";
import GooeyText from "./GooeyText";
import sequenceReportMock from "../mocks/sequenceReport.json";

const VIEW = {
  LOGIN: "login",
  LOOKUP: "lookup",
};

const normalizeApiBase = (value) => (value ?? "").replace(/\/+$/g, "");
const API_IOT_BASE_URL = normalizeApiBase(import.meta.env.VITE_API_IOT_BASE_URL);

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
      return "—";
    default:
      return "•";
  }
};

const getSummaryTagDescription = (tag) => {
  switch (tag) {
    case "STABLE":
      return "주요/보조 관절 모두 일관됩니다.";
    case "VARIABLE":
      return "주요 과제는 가능하나 안정성 변동이 있습니다.";
    case "UNSTABLE":
      return "수행 또는 안전성에 반복적 문제가 있습니다.";
    default:
      return "-";
  }
};

const getTrendDescription = (trend) => {
  switch (trend) {
    case "IMPROVING":
      return "세션 진행에 따라 수행이 개선됩니다.";
    case "STABLE":
      return "세션 내 큰 변화 없이 유지됩니다.";
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
      const useMock = String(import.meta.env.VITE_USE_MOCK).toLowerCase() === "true";
      if (useMock) {
        const data = {
          therapistId: Number(trimmedId) || 1,
          therapistName: "김닥터",
          patients: [
            {
              patientId: 103,
              name: "박재활",
              gender: "MALE",
              age: 41,
              diseaseName: "뇌졸중",
            },
            {
              patientId: 105,
              name: "정이온",
              gender: "FEMALE",
              age: 45,
              diseaseName: "신경 손상",
            },
            {
              patientId: 120,
              name: "김민수",
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

  const loadReport = async (patient) => {
    if (!patient) return;
    setReportLoading(true);
    setReportError("");
    setExpandedExercise(null);
    try {
      const useMock = String(import.meta.env.VITE_USE_MOCK).toLowerCase() === "true";
      if (useMock) {
        setReportData({
          profile: {
            patient_id: patient.patientId,
            name: patient.name,
            birth_date: "1988-05-20",
            gender: patient.gender,
            disease_name: patient.diseaseName,
            rehab_phase: "MIDDLE",
            created_at: "2026-01-15T10:00:00",
          },
          reportInput: sequenceReportMock,
          sequences: [
            {
              sequence_id: 401,
              started_at: "2026-01-30T14:00:00",
              ended_at: "2026-01-30T14:40:00",
              feedback: "후반부 안정성 붕괴 패턴이 반복 관찰됨.",
            },
            {
              sequence_id: 398,
              started_at: "2026-01-27T10:00:00",
              ended_at: "2026-01-27T10:35:00",
              feedback: "상체 기울기 변동 증가 확인.",
            },
          ],
        });
        return;
      }

      const [profileRes, sequencesRes, reportRes] = await Promise.all([
        fetch(`${API_IOT_BASE_URL}/api/patients/${patient.patientId}`, { method: "GET" }),
        fetch(`${API_IOT_BASE_URL}/api/patients/${patient.patientId}/sequences`, { method: "GET" }),
        fetch(`${API_IOT_BASE_URL}/api/therapist/patient/${patient.patientId}/report`, {
          method: "GET",
        }),
      ]);

      if (!profileRes.ok) throw new Error("환자 정보를 불러오지 못했습니다.");

      const profilePayload = await profileRes.json();
      const sequencesPayload = sequencesRes.ok ? await sequencesRes.json() : { data: [] };
      const reportPayload = reportRes.ok ? await reportRes.json() : { data: null };

      const sequences = Array.isArray(sequencesPayload?.data) ? sequencesPayload.data : [];

      setReportData({
        profile: profilePayload?.data ?? null,
        sequences,
        reportInput: reportPayload?.data ?? null,
      });
    } catch (err) {
      setReportError("리포트를 불러오는 데 실패했습니다.");
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
                  placeholder="환자 번호 또는 이름을 입력하세요"
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
                            {reportData.profile.name ?? reportData.reportInput?.patientName ?? "-"} 
                            (ID {reportData.profile.patient_id}) | {" "}
                            {reportData.profile.gender === "MALE" ? "M" : "F"} |{" "}
                            {calcAge(reportData.profile.birth_date) ?? "-"}세
                            <br />
                            질환: {reportData.profile.disease_name} | 단계:{" "}
                            {reportData.reportInput?.rehabPhase ?? reportData.profile.rehab_phase ?? "-"} | 대상 측면: {" "}
                            {reportData.reportInput?.side ?? "-"}
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
                              세션 개수:{" "}
                              {reportData.reportInput.overallSummary?.totalExercises ?? "-"}
                            </span>{" "}
                            |{" "}
                            <span>
                              기록일:{" "}
                              {formatDateTime(reportData.reportInput.date)}
                            </span>
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
                                    onClick={() => setExpandedExercise(isOpen ? null : key)}
                                    aria-expanded={isOpen}
                                  >
                                    <div className="exercise-title">
                                      <span>{exercise.exerciseName ?? "-"}</span>
                                      <span className={getSummaryTagClass(exercise.summaryTag)}>
                                        {exercise.summaryTag ?? "-"}
                                      </span>
                                      <span className={getTrendClass(exercise.withinSessionTrend)}>
                                        {getTrendSymbol(exercise.withinSessionTrend)} {exercise.withinSessionTrend ?? "-"}
                                      </span>
                                    </div>
                                    <div className="exercise-meta">
                                      <span className="meta-pill-compact">
                                        성공 비율 {formatPercent(exercise.performance?.successRate)}
                                      </span>
                                      <span className="meta-pill-compact">
                                        평균 점수 {formatNumber(exercise.performance?.averageScore)}
                                      </span>
                                      <span className="exercise-toggle">{isOpen ? "접기" : "보기"}</span>
                                    </div>
                                  </button>
                                  {isOpen && (
                                    <div className="exercise-body">
                                      <div className="exercise-note">
                                        {exercise.sessionNote ?? "-"}
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
                                        <div className="exercise-muted">주요 관찰 내용이 없습니다.</div>
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
                                              {getTrendSymbol(
                                                exercise.comparisonToPrevious.trend
                                              )} {exercise.comparisonToPrevious.trend ?? "-"}
                                            </span>
                                            <span className="exercise-compare-text">
                                              {exercise.comparisonToPrevious.trendDescription ?? "-"}
                                            </span>
                                          </>
                                        ) : (
                                          <span className="tag tag--muted">이전 세션과 비교 데이터가 없습니다.</span>
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
                          <div className="therapist-empty">최근 시퀀스가 없습니다.</div>
                        )}
                      </div>
                    </div>
                  </>
                )}{!reportLoading && !reportError && !selectedPatient && (
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
