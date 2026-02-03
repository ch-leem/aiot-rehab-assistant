import { useMemo, useState } from "react";
import MainLayout from "./MainLayout";
import GooeyText from "./GooeyText";

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

export default function TherapistUI() {
  const [view, setView] = useState(VIEW.LOGIN);
  const [therapistId, setTherapistId] = useState("");
  const [therapistName, setTherapistName] = useState("");
  const [patients, setPatients] = useState([]);
  const [searchValue, setSearchValue] = useState("");
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");
  const [reportData, setReportData] = useState({
    profile: null,
    sequences: [],
    sequenceSummary: null,
    reportSummary: null,
    exercises: [],
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
              patientId: 101,
              name: "홍길동",
              gender: "MALE",
              age: 30,
              diseaseName: "뇌졸중",
            },
            {
              patientId: 105,
              name: "홍길순",
              gender: "FEMALE",
              age: 45,
              diseaseName: "파킨슨",
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
          sequences: [
            {
              sequence_id: 101,
              started_at: "2026-01-20T14:30:00",
              ended_at: "2026-01-20T15:10:00",
              feedback: "전반적으로 가동 범위가 향상됨",
            },
            {
              sequence_id: 105,
              started_at: "2026-01-22T09:00:00",
              ended_at: "2026-01-22T09:45:00",
              feedback: "통증 완화 확인",
            },
          ],
          sequenceSummary: {
            sequence_id: 101,
            started_at: "2026-01-20T14:30:00",
            ended_at: "2026-01-20T15:10:00",
            feedback: "가동 범위 향상. 보상 동작이 줄고 안정성이 높아졌습니다.",
            summary: {
              total_trials: 50,
              success_trials: 42,
              avg_angle: 115.5,
              in_target_rate: 84.0,
              compensation_total: 5,
              stability_level: "STABLE",
            },
          },
          reportSummary: {
            totalTrials: 50,
            successTrials: 42,
            avgAngle: 115.5,
            inTargetRate: 84.0,
            stabilityLevel: "STABLE",
          },
          exercises: [
            {
              exercise_id: 5,
              exercise_name: "팔꿈치 굴곡 운동",
              description: "앉은 자세에서 팔꿈치를 천천히 굽히는 운동입니다.",
              precautions: "어깨가 위로 들리지 않도록 주의하세요.",
              side: "RIGHT",
              goal_vision: "140",
              goal_sensor: "135",
            },
          ],
        });
        return;
      }

      const [profileRes, sequencesRes, reportRes, exercisesRes] = await Promise.all([
        fetch(`${API_IOT_BASE_URL}/api/patients/${patient.patientId}`, { method: "GET" }),
        fetch(`${API_IOT_BASE_URL}/api/patients/${patient.patientId}/sequences`, { method: "GET" }),
        fetch(`${API_IOT_BASE_URL}/api/therapist/patient/${patient.patientId}/report`, {
          method: "GET",
        }),
        fetch(`${API_IOT_BASE_URL}/api/patients/${patient.patientId}/exercises`, {
          method: "GET",
        }),
      ]);

      if (!profileRes.ok) throw new Error("환자 정보를 불러오지 못했습니다.");

      const profilePayload = await profileRes.json();
      const sequencesPayload = sequencesRes.ok ? await sequencesRes.json() : { data: [] };
      const reportPayload = reportRes.ok ? await reportRes.json() : { data: null };
      const exercisesPayload = exercisesRes.ok ? await exercisesRes.json() : { data: [] };

      const sequences = Array.isArray(sequencesPayload?.data) ? sequencesPayload.data : [];
      const latestSequence = sequences
        .slice()
        .sort(
          (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
        )[0];

      let sequenceSummary = null;
      if (latestSequence?.sequence_id) {
        const summaryRes = await fetch(
          `${API_IOT_BASE_URL}/api/patients/sequences/${latestSequence.sequence_id}`,
          { method: "GET" }
        );
        if (summaryRes.ok) {
          const summaryPayload = await summaryRes.json();
          sequenceSummary = summaryPayload?.data ?? null;
        }
      }

      setReportData({
        profile: profilePayload?.data ?? null,
        sequences,
        sequenceSummary,
        reportSummary: reportPayload?.data ?? null,
        exercises: Array.isArray(exercisesPayload?.data) ? exercisesPayload.data : [],
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
                    sequenceSummary: null,
                    reportSummary: null,
                    exercises: [],
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
                      <div className="report-card-title">환자 요약</div>
                      <div className="report-card-body">
                        {reportData.profile ? (
                          <>
                            환자 번호 {reportData.profile.patient_id} /{" "}
                            {reportData.profile.gender === "MALE" ? "남" : "여"} /{" "}
                            {calcAge(reportData.profile.birth_date) ?? "-"}세
                            <br />
                            병명: {reportData.profile.disease_name} / 단계:{" "}
                            {reportData.profile.rehab_phase}
                          </>
                        ) : (
                          "환자 정보를 불러오지 못했습니다."
                        )}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">종합 리포트</div>
                      <div className="report-card-body">
                        {reportData.reportSummary ? (
                          <>
                            총 시도 {reportData.reportSummary.totalTrials}회 · 성공{" "}
                            {reportData.reportSummary.successTrials}회
                            <br />
                            평균 각도 {reportData.reportSummary.avgAngle}° · 목표 진입률{" "}
                            {reportData.reportSummary.inTargetRate}% · 안정성{" "}
                            {reportData.reportSummary.stabilityLevel}
                          </>
                        ) : (
                          "종합 리포트를 불러오지 못했습니다."
                        )}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">오늘 시퀀스 요약</div>
                      <div className="report-card-body">
                        {reportData.sequenceSummary ? (
                          <>
                            총 시도 {reportData.sequenceSummary.summary?.total_trials ?? "-"}회 · 성공{" "}
                            {reportData.sequenceSummary.summary?.success_trials ?? "-"}회
                            <br />
                            평균 각도 {reportData.sequenceSummary.summary?.avg_angle ?? "-"}° · 목표 진입률{" "}
                            {reportData.sequenceSummary.summary?.in_target_rate ?? "-"}%
                            <br />
                            보상 동작 {reportData.sequenceSummary.summary?.compensation_total ?? "-"}회 · 안정성{" "}
                            {reportData.sequenceSummary.summary?.stability_level ?? "-"}
                            <div className="report-note">
                              {reportData.sequenceSummary.feedback}
                            </div>
                          </>
                        ) : (
                          "시퀀스 요약을 불러오지 못했습니다."
                        )}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title-row">
                        <div className="report-card-title">주요 위험 신호</div>
                        <button
                          className="therapist-fail-button"
                          type="button"
                          onClick={() => {
                            const patientQuery = selectedPatient?.patientId
                              ? `?patientId=${selectedPatient.patientId}`
                              : "";
                            window.location.href = `/therapist/fail_3D${patientQuery}`;
                          }}
                        >
                          실패분석
                        </button>
                      </div>
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
                                          const scoreValues = tries
                                            .map((t) => Number(t.totalScore))
                                            .filter((v) => Number.isFinite(v));
                                          const maxVal = scoreValues.length
                                            ? Math.max(...scoreValues)
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
                                              {scoreValues.length > 0 && (
                                                <>
                                                  <div className="session-trend">
                                                    <div className="session-scale">
                                                      <span>100</span>
                                                      <span>50</span>
                                                      <span>0</span>
                                                    </div>
                                                    {(() => {
                                                      const points = scoreValues.map((val, i) => {
                                                        const x =
                                                          scoreValues.length === 1
                                                            ? 50
                                                            : (i / (scoreValues.length - 1)) * 100;
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
                          <div className="therapist-empty">최근 기록이 없습니다.</div>
                        )}
                      </div>
                    </div>
                    <div className="report-card">
                      <div className="report-card-title">처방 운동</div>
                      <div className="report-list">
                        {reportData.exercises.length > 0 ? (
                          reportData.exercises.map((exercise) => (
                            <div key={exercise.mapping_id ?? exercise.exercise_id} className="report-list-row">
                              <span>{exercise.exercise_name}</span>
                              <span>
                                {exercise.side} · 목표 {exercise.goal_vision}/{exercise.goal_sensor}
                              </span>
                            </div>
                          ))
                        ) : (
                          <div className="therapist-empty">처방 운동이 없습니다.</div>
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
