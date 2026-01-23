import { useEffect, useMemo, useState } from "react";
import "./App.css";
import MainLayout from "./components/MainLayout";
import PatientCheck from "./components/PatientCheck";
import Login from "./components/Login";
import TherapistUI from "./components/TherapistUI";

const SCREEN = {
  LOGIN: "login",
  PATIENT_CHECK: "patient-check",
  EXERCISE_LIST: "exercise-list",
  EXERCISE_INTRO: "exercise-intro",
  EXERCISE_SESSION: "exercise-session",
  EXERCISE_RESULT: "exercise-result",
};

const EXERCISES = [
  {
    title: "팔 들어 올리기",
    duration: "약 3분",
    caution: "어깨가 올라가지 않도록 자연스럽게 움직여주세요.",
    instruction: "팔을 천천히 들어 올리고 2초 유지한 뒤 내려주세요.",
  },
  {
    title: "팔 내리기",
    duration: "약 2분",
    caution: "호흡을 유지하면서 천천히 내려주세요.",
    instruction: "팔을 천천히 내려 바닥을 향해 편안하게 움직여주세요.",
  },
  {
    title: "팔 좌우 이동",
    duration: "약 2분",
    caution: "몸통은 고정한 채 팔만 움직여주세요.",
    instruction: "팔을 좌우로 천천히 이동하며 범위를 유지해주세요.",
  },
];

const RESULT_RULES = [
  {
    min: 0,
    max: 2,
    summary: "오늘은 몸을 풀어보는 연습을 했어요.",
    change: "오늘은 몸을 푸는 데 집중했어요.",
    next: "다음에는 천천히 같은 동작을 다시 해볼게요.",
    tag: "수고",
  },
  {
    min: 3,
    max: 5,
    summary: "오늘은 동작을 익히는 연습을 했어요.",
    change: "동작 흐름을 천천히 익혀가는 중이에요.",
    next: "같은 방법으로 조금 더 시도해볼게요.",
    tag: "꾸준히",
  },
  {
    min: 6,
    max: 7,
    summary: "오늘은 대부분의 동작을 잘 수행했어요.",
    change: "움직임이 이전보다 안정적으로 느껴졌어요.",
    next: "다음에는 같은 동작을 조금 더 안정적으로 해볼게요.",
    tag: "안정",
  },
  {
    min: 8,
    max: 9,
    summary: "오늘은 동작을 안정적으로 잘 수행했어요.",
    change: "동작이 더 부드럽게 이어졌어요.",
    next: "다음에는 모든 동작을 완성해볼 수 있어요.",
    tag: "좋아요",
  },
  {
    min: 10,
    max: 10,
    summary: "오늘 목표한 동작을 모두 완료했어요.",
    change: "흐름이 매끄럽게 이어졌어요.",
    next: "다음 운동도 같은 방법으로 진행하면 됩니다.",
    tag: "완료",
  },
];

export default function App() {
  const isTherapistRoute =
    typeof window !== "undefined" &&
    window.location.pathname.startsWith("/therapist");
  const [screen, setScreen] = useState(SCREEN.LOGIN);
  const [patientId, setPatientId] = useState("");
  const [nurseId, setNurseId] = useState("");
  const stageTotal = 5;
  const [postureChecked, setPostureChecked] = useState(false);
  const [exerciseIndex, setExerciseIndex] = useState(0);
  const [setIndex, setSetIndex] = useState(1);
  const [countdown, setCountdown] = useState(0);
  const autoSeconds = 5;

  const stageLabel = useMemo(() => {
    switch (screen) {
      case SCREEN.EXERCISE_RESULT:
        return "운동 결과 단계";
      case SCREEN.EXERCISE_SESSION:
        return "운동 진행 단계";
      case SCREEN.EXERCISE_INTRO:
        return "운동 설명 단계";
      case SCREEN.EXERCISE_LIST:
        return "운동 목록 단계";
      case SCREEN.PATIENT_CHECK:
        return "환자 확인 단계";
      case SCREEN.LOGIN:
      default:
        return "로그인";
    }
  }, [screen]);

  const stageIndex = useMemo(() => {
    switch (screen) {
      case SCREEN.PATIENT_CHECK:
        return 1;
      case SCREEN.EXERCISE_LIST:
        return 2;
      case SCREEN.EXERCISE_INTRO:
        return 3;
      case SCREEN.EXERCISE_SESSION:
        return 4;
      case SCREEN.EXERCISE_RESULT:
        return 5;
      case SCREEN.LOGIN:
      default:
        return null;
    }
  }, [screen]);

  const handleLogin = ({ nextPatientId, nextNurseId }) => {
    setPatientId(nextPatientId);
    setNurseId(nextNurseId);
    setExerciseIndex(0);
    setScreen(SCREEN.PATIENT_CHECK);
  };

  const moveToExerciseIntro = () => {
    setPostureChecked(false);
    setScreen(SCREEN.EXERCISE_INTRO);
  };

  const currentExercise = EXERCISES[exerciseIndex];
  const successCount = 8;
  const resultRule =
    RESULT_RULES.find(
      (rule) => successCount >= rule.min && successCount <= rule.max
    ) ?? RESULT_RULES[0];

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_LIST) {
      setCountdown(0);
      return;
    }
    const endTime = Date.now() + autoSeconds * 1000;
    const tick = () => {
      const next = Math.max(1, Math.ceil((endTime - Date.now()) / 1000));
      setCountdown(next);
    };
    tick();
    const interval = setInterval(tick, 250);
    const timeout = setTimeout(() => {
      moveToExerciseIntro();
    }, autoSeconds * 1000);
    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [screen, autoSeconds]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_INTRO) return;
    setPostureChecked(false);
    const timeout = setTimeout(() => {
      setPostureChecked(true);
    }, 6000);
    return () => clearTimeout(timeout);
  }, [screen, exerciseIndex]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_INTRO || !postureChecked) return;
    const timeout = setTimeout(() => {
      setScreen(SCREEN.EXERCISE_SESSION);
    }, 1200);
    return () => clearTimeout(timeout);
  }, [screen, postureChecked]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION) return;
    setSetIndex(1);
  }, [screen, exerciseIndex]);

  if (isTherapistRoute) {
    return <TherapistUI />;
  }

  return (
    <MainLayout
      stageLabel={stageLabel}
      patientId={patientId}
      nurseId={nurseId}
      stageIndex={stageIndex}
      stageTotal={stageTotal}
      hideCamera={screen === SCREEN.EXERCISE_RESULT}
    >
      {screen === SCREEN.LOGIN && <Login onSubmit={handleLogin} />}
      {screen === SCREEN.PATIENT_CHECK && (
        <PatientCheck
          onStart={() => {
            setExerciseIndex(0);
            setScreen(SCREEN.EXERCISE_LIST);
          }}
          onBack={() => setScreen(SCREEN.LOGIN)}
        />
      )}
      {screen === SCREEN.EXERCISE_LIST && (
        <div className="placeholder-screen enter">
          <div className="screen-label">오늘의 운동</div>
          <h1>오늘의 재활 운동</h1>
          <p className="lead">
            오늘 해야 할 3가지 동작이 준비되어 있습니다.
          </p>
          <div className="auto-hint">
            5초 뒤에 운동 설명으로 넘어갑니다{" "}
            <strong className="countdown-chip">{countdown}초</strong>
          </div>
          <div className="placeholder-card">
            <div>
              <div className="card-title">1. 팔 들어 올리기</div>
              <div className="card-meta">예상 3분</div>
            </div>
            <span className="card-badge">대표 동작</span>
          </div>
          <div className="placeholder-card muted">
            <div>
              <div className="card-title">2. 팔 내리기</div>
              <div className="card-meta">예상 2분</div>
            </div>
            <span className="card-badge subtle">대기</span>
          </div>
          <div className="placeholder-card muted">
            <div>
              <div className="card-title">3. 팔 좌우 이동</div>
              <div className="card-meta">예상 2분</div>
            </div>
            <span className="card-badge subtle">대기</span>
          </div>
          <div className="cta-row">
            <button
              className="ghost-button"
              type="button"
              onClick={() => setScreen(SCREEN.PATIENT_CHECK)}
            >
              환자 확인으로
            </button>
            <button
              className="primary-button"
              type="button"
              onClick={moveToExerciseIntro}
            >
              지금 시작
            </button>
          </div>
        </div>
      )}
      {screen === SCREEN.EXERCISE_INTRO && (
        <div className="placeholder-screen exercise-intro enter">
          <div className="screen-label">운동 설명</div>
          <h1>{currentExercise.title}</h1>
          <p className="lead">{currentExercise.instruction}</p>
          <div className="info-grid single">
            <div className="info-card">
              <div>
                <div className="card-title">주의사항</div>
                <div className="card-meta">
                  {currentExercise.caution}
                </div>
              </div>
            </div>
          </div>
          <div className="check-row">
            <div>
              <div className="card-title">자세 확인</div>
              <div className="card-meta">
                카메라 화면에 팔과 어깨가 모두 보이면 자동으로 넘어갑니다.
              </div>
            </div>
            <button
              className="ghost-button"
              type="button"
              onClick={() => setPostureChecked(true)}
              disabled={postureChecked}
            >
              {postureChecked ? "인식 완료" : "인식 확인"}
            </button>
          </div>
          <div className="auto-hint">
            {postureChecked
              ? "인식 완료. 곧 운동을 시작합니다."
              : "인식 대기 중입니다."}
          </div>
          <div className="cta-row">
            <button
              className="ghost-button"
              type="button"
              onClick={() => setScreen(SCREEN.EXERCISE_LIST)}
            >
              목록으로
            </button>
            <button
              className="primary-button"
              type="button"
              onClick={() => setScreen(SCREEN.EXERCISE_SESSION)}
              disabled={!postureChecked}
            >
              바로 시작
            </button>
          </div>
        </div>
      )}
      {screen === SCREEN.EXERCISE_SESSION && (
        <div className="placeholder-screen exercise-session enter">
          <div className="screen-label">운동 진행</div>
          <div className="session-visual">
            3D 반응형 화면 자리
          </div>
          <div className="session-panel session-panel-next">
            <div className="session-bar">
              <span />
            </div>
            <div className="card-meta">현재 {setIndex}/3 세트</div>
          </div>
          <button
            className="ghost-button session-next"
            type="button"
            onClick={() => {
              if (exerciseIndex < EXERCISES.length - 1) {
                setExerciseIndex((prev) => prev + 1);
                setScreen(SCREEN.EXERCISE_INTRO);
              } else {
                setScreen(SCREEN.EXERCISE_RESULT);
              }
            }}
          >
            다음 단계
          </button>
        </div>
      )}
      {screen === SCREEN.EXERCISE_RESULT && (
        <div className="placeholder-screen result-screen enter">
          <div className="result-layout">
            <section className="result-left">
              <div className="result-left-inner">
                <div className="screen-label">운동 결과</div>
                <h1>오늘의 기록</h1>
                <p className="lead">{resultRule.summary}</p>
                <div className="info-grid single result-cards">
                  <div className="info-card accent">
                    <div>
                      <div className="card-title">오늘의 성과</div>
                      <div className="card-meta">{resultRule.summary}</div>
                    </div>
                    <span className="card-badge">{resultRule.tag}</span>
                  </div>
                  <div className="info-card">
                    <div>
                      <div className="card-title">전과 달라진 점</div>
                      <div className="card-meta change-split">
                        <div className="change-item upper">
                          상체 운동: 안정감이 조금 더 이어졌어요.
                        </div>
                        <div className="change-item lower">
                          하체 운동: 움직임 범위가 일정해졌어요.
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="info-card">
                    <div>
                      <div className="card-title">앞으로의 목표</div>
                      <div className="card-meta">{resultRule.next}</div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
            <section className="result-right">
              <div className="result-top-actions">
                <button
                  className="primary-button"
                  type="button"
                  onClick={() => setScreen(SCREEN.PATIENT_CHECK)}
                >
                  오늘 마치기
                </button>
              </div>
              <div className="chart-card">
                <div className="card-title">상체 + 하체 성공 횟수</div>
                <div className="card-meta">오늘 수행한 전체 동작 기준</div>
                <div className="donut-grid">
                  <div className="donut-item">
                    <div className="donut-wrap">
                      <div className="donut upper" style={{ "--fill": "83%" }} />
                    </div>
                    <div className="donut-text">
                      <div className="donut-value">10/12</div>
                      <div className="donut-label">
                        <span className="legend-dot upper" />
                        상체 성공
                      </div>
                    </div>
                  </div>
                  <div className="donut-item">
                    <div className="donut-wrap">
                      <div className="donut lower" style={{ "--fill": "66%" }} />
                    </div>
                    <div className="donut-text">
                      <div className="donut-value">8/12</div>
                      <div className="donut-label">
                        <span className="legend-dot lower" />
                        하체 성공
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="chart-card">
                <div className="card-title">최근 5번 정확도 추이</div>
                <div className="bar-chart">
                  <div className="bar bar-1" />
                  <div className="bar bar-2" />
                  <div className="bar bar-3" />
                  <div className="bar bar-4" />
                  <div className="bar bar-5" />
                </div>
              </div>
            </section>
          </div>
        </div>
      )}
    </MainLayout>
  );
}
