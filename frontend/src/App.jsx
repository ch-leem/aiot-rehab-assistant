import { useMemo, useState } from "react";
import "./App.css";
import MainLayout from "./components/MainLayout";
import PatientCheck from "./components/PatientCheck";
import Login from "./components/Login";

const SCREEN = {
  LOGIN: "login",
  PATIENT_CHECK: "patient-check",
  EXERCISE_LIST: "exercise-list",
  EXERCISE_INTRO: "exercise-intro",
  EXERCISE_SESSION: "exercise-session",
  EXERCISE_RESULT: "exercise-result",
};

export default function App() {
  const [screen, setScreen] = useState(SCREEN.LOGIN);
  const [patientId, setPatientId] = useState("");
  const [nurseId, setNurseId] = useState("");
  const stageTotal = 5;
  const [postureChecked, setPostureChecked] = useState(false);

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
    setScreen(SCREEN.PATIENT_CHECK);
  };

  const moveToExerciseIntro = () => {
    setPostureChecked(false);
    setScreen(SCREEN.EXERCISE_INTRO);
  };

  return (
    <MainLayout
      stageLabel={stageLabel}
      patientId={patientId}
      nurseId={nurseId}
      stageIndex={stageIndex}
      stageTotal={stageTotal}
    >
      {screen === SCREEN.LOGIN && <Login onSubmit={handleLogin} />}
      {screen === SCREEN.PATIENT_CHECK && (
        <PatientCheck
          onStart={() => setScreen(SCREEN.EXERCISE_LIST)}
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
            <button className="primary-button" type="button" onClick={moveToExerciseIntro}>
              운동 설명 보기
            </button>
          </div>
        </div>
      )}
      {screen === SCREEN.EXERCISE_INTRO && (
        <div className="placeholder-screen enter">
          <div className="screen-label">운동 설명</div>
          <h1>팔 들어 올리기</h1>
          <p className="lead">
            팔을 천천히 들어 올리고 2초 유지한 뒤 내려주세요.
          </p>
          <div className="info-grid single">
            <div className="info-card">
              <div>
                <div className="card-title">주의사항</div>
                <div className="card-meta">
                  어깨가 올라가지 않도록 자연스럽게 움직여주세요.
                </div>
              </div>
            </div>
          </div>
          <div className="check-row">
            <div>
              <div className="card-title">자세 확인</div>
              <div className="card-meta">
                카메라 화면에 팔과 어깨가 모두 들어오면 확인을 눌러주세요.
              </div>
            </div>
            <button
              className="ghost-button"
              type="button"
              onClick={() => setPostureChecked(true)}
              disabled={postureChecked}
            >
              {postureChecked ? "확인 완료" : "자세 확인"}
            </button>
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
              운동 시작
            </button>
          </div>
        </div>
      )}
      {screen === SCREEN.EXERCISE_SESSION && (
        <div className="placeholder-screen enter">
          <div className="screen-label">운동 진행</div>
          <h1>동작 진행 중</h1>
          <p className="lead">손의 움직임에 따라 화면이 반응합니다.</p>
          <div className="session-panel">
            <div className="session-bar">
              <span />
            </div>
            <div className="card-meta">현재 1/3 세트</div>
          </div>
          <div className="cta-row">
            <button
              className="ghost-button"
              type="button"
              onClick={() => setScreen(SCREEN.EXERCISE_INTRO)}
            >
              설명으로
            </button>
            <button
              className="primary-button"
              type="button"
              onClick={() => setScreen(SCREEN.EXERCISE_RESULT)}
            >
              결과 보기
            </button>
          </div>
        </div>
      )}
      {screen === SCREEN.EXERCISE_RESULT && (
        <div className="placeholder-screen enter">
          <div className="screen-label">운동 결과</div>
          <h1>오늘의 결과</h1>
          <p className="lead">첫 번째 동작을 잘 마쳤습니다.</p>
          <div className="info-grid single">
            <div className="info-card accent">
              <div>
                <div className="card-title">완료</div>
                <div className="card-meta">정확도 92% · 3세트</div>
              </div>
              <span className="card-badge">좋아요</span>
            </div>
          </div>
          <div className="cta-row">
            <button
              className="ghost-button"
              type="button"
              onClick={() => setScreen(SCREEN.EXERCISE_LIST)}
            >
              목록으로
            </button>
            <button className="primary-button" type="button">
              다음 운동
            </button>
          </div>
        </div>
      )}
    </MainLayout>
  );
}
