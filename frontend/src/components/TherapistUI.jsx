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
                      <div className="report-card-title">
                        환자 요약
                        <button
                          className="therapist-ghost"
                          type="button"
                          onClick={() => {
                            if (!selectedPatient?.patientId) return;
                            window.location.href = `/therapist/fail_type?patientId=${selectedPatient.patientId}`;
                          }}
                          disabled={!selectedPatient?.patientId}
                          style={{ float: "right" }}
                        >
                          실패유형
                        </button>
                      </div>
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
                      <div className="report-card-title">최근 시퀀스 기록</div>
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
