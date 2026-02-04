import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import "./App.css";
import MainLayout from "./components/MainLayout";
import PatientCheck from "./components/PatientCheck";
import Login from "./components/Login";
import TherapistUI from "./components/TherapistUI";
import ArmRaiseGame from "./components/ArmRaiseGame";
import MoleGame from "./components/MoleGame";

const SCREEN = {
  LOGIN: "login",
  PATIENT_CHECK: "patient-check",
  EXERCISE_LIST: "exercise-list",
  EXERCISE_INTRO: "exercise-intro",
  EXERCISE_SESSION: "exercise-session",
  EXERCISE_RESULT: "exercise-result",
};

const EXERCISE_CATALOG = {
  1: {
    title: "팔 들어올리기 운동",
    duration: "예상 3분",
    caution: "어깨가 올라가지 않도록 자연스럽게 움직여주세요.",
    instruction: "팔을 천천히 들어 올리고 2초 유지한 뒤 내려주세요.",
  },
  2: {
    title: "하체 힘 회복 운동",
    duration: "예상 3분",
    caution: "무릎이 과하게 앞으로 나가지 않도록 천천히 진행해주세요.",
    instruction: "하체에 힘을 주며 천천히 움직이고 균형을 유지해주세요.",
  },
};
const normalizeApiBase = (value) => (value ?? "").replace(/\/+$/g, "");
const API_USER_BASE_URL = normalizeApiBase(import.meta.env.VITE_API_USER_BASE_URL);

const RESULT_RULES = [
  {
    min: 0,
    max: 2,
    summary: "오늘은 몸을 풀어보는 연습을 했어요.",
    change: "오늘은 몸을 푸는 데 집중했어요.",
    next: "다음에는 천천히 같은 동작을 다시 해볼게요.",
    tag: "준비",
  },
  {
    min: 3,
    max: 5,
    summary: "오늘은 동작을 익히는 연습을 했어요.",
    change: "동작 흐름을 천천히 이어가는 중이에요.",
    next: "같은 방법으로 조금 더 시도해볼게요.",
    tag: "적응",
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
    change: "동작 흐름이 부드럽게 이어졌어요.",
    next: "다음에는 모든 동작을 완성해볼 수 있어요.",
    tag: "좋아요",
  },
  {
    min: 10,
    max: 10,
    summary: "오늘 목표한 동작을 모두 완료했어요.",
    change: "이전보다 자신 있게 움직였어요.",
    next: "다음 운동도 같은 방법으로 진행하면 됩니다.",
    tag: "완료",
  },
];

export default function App() {
  const useMock = String(import.meta.env.VITE_USE_MOCK).toLowerCase() === "true";
  const isTherapistRoute =
    typeof window !== "undefined" &&
    window.location.pathname.startsWith("/therapist");
  const [screen, setScreen] = useState(SCREEN.LOGIN);
  const [patientId, setPatientId] = useState("");
  const [nurseId, setNurseId] = useState("");
  const [therapistName, setTherapistName] = useState("");
  const [patientName, setPatientName] = useState("");
  const [diseaseName, setDiseaseName] = useState("");
  const [rehabPhase, setRehabPhase] = useState("");
  const [exerciseIds, setExerciseIds] = useState([]);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [loginError, setLoginError] = useState("");
  const stageTotal = 5;
  const [postureChecked, setPostureChecked] = useState(false);
  const [guideEnded, setGuideEnded] = useState(false);
  const [exerciseIndex, setExerciseIndex] = useState(0);
  const [setIndex, setSetIndex] = useState(1);
  const [exerciseDetails, setExerciseDetails] = useState({});
  const [sequenceId, setSequenceId] = useState(null);
  const [sequenceSessions, setSequenceSessions] = useState([]);
  const [startedSessionId, setStartedSessionId] = useState(null);
  const [tryIndex, setTryIndex] = useState(0);
  const [armRaiseCount, setArmRaiseCount] = useState(0);
  const [armRaiseTotal, setArmRaiseTotal] = useState(10);
  const [armRaiseFeedback, setArmRaiseFeedback] = useState(null);
  const [lowerBodyFeedback, setLowerBodyFeedback] = useState(null);
  const [moleGameCount, setMoleGameCount] = useState(0);
  const [moleGameTotal, setMoleGameTotal] = useState(10);
  const [holdingPower, setHoldingPower] = useState(0);
  const [exerciseCompleteFeedback, setExerciseCompleteFeedback] = useState(null);
  const [sensorPower, setSensorPower] = useState(null);
  const [countdownStep, setCountdownStep] = useState(null);
  const [moleTrySignal, setMoleTrySignal] = useState(0);
  const patientWeight = 50;
  const requiredPower = patientWeight * 0.7;
  const autoAdvanceRef = useRef(false);
  const moleAutoAdvanceRef = useRef(false);
  const molePreloadRef = useRef(false);
  const exerciseCompleteTimerRef = useRef(null);
  const countdownTimerRef = useRef(null);
  const countdownActiveRef = useRef(false);
  const lastCountdownTryRef = useRef(null);
  const countdownTokenRef = useRef(0);
  const sessionStartSentRef = useRef(null);
  const startedTryRef = useRef(null);
  const lastStartedTryIndexRef = useRef(-1);
  const armRaiseTimeoutRef = useRef(null);
  const moleTryTimeoutRef = useRef(null);
  const lastArmRaiseCountRef = useRef(0);
  const armRaiseCompleteRef = useRef(false);
  const prevTryIndexRef = useRef(0);
  const armRaiseCompleteTimerRef = useRef(null);
  const lowerBodyFeedbackTimerRef = useRef(null);
  const allowSessionExitRef = useRef(false);
  const lastMoleCountRef = useRef(0);
  const [activeTryId, setActiveTryId] = useState(null);
  const [compareItems, setCompareItems] = useState([]);
  const [sequenceAverages, setSequenceAverages] = useState([]);
  const [recentGoals, setRecentGoals] = useState([]);
  const [tryScores, setTryScores] = useState({});

  const audioRef = useRef(null);

  const playFailAudio = useCallback((failId) => {
    const AUDIO_MAP = {
      F_SH_FLEX: "/audio/F_SH_FLEX_팔을_더_들어주세요.mp3",
      F_EL_EXT: "/audio/F_EL_EXT_팔을_편_상태로_운동해주세요.mp3",
      F_TR_TILT: "/audio/F_TR_TILT_허리를_펴주세요.mp3",
      F_SH_HOR: "/audio/F_SH_HOR_어깨를_맞춰주세요.mp3",
      F_ACCEL: "/audio/F_ACCEL_팔을_천천히_들어주세요.mp3",
      F_PR_LOAD: "/audio/F_PR_LOAD_발에_힘을_더_주세요.mp3",
      F_PL_HOR: "/audio/F_PL_HOR_골반을_맞춰주세요.mp3",
      F_ANK_STB: "/audio/F_ANK_STB_반대쪽_발에_발목을_고정해주세요.mp3",
      F_ELSE: "/audio/F_ELSE_예외_발생_예외_발생.mp3",
      SUCCESS: "/audio/T_잘하셨어요.mp3",
      3: "/audio/3_삼.mp3",
      2: "/audio/2_이.mp3",
      1: "/audio/1_일.mp3",
      시작: "/audio/시작_시작.mp3"
    };

    const src = AUDIO_MAP[failId] || AUDIO_MAP.F_ELSE;

    try {
      if (!audioRef.current) audioRef.current = new Audio();
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current.src = src;
      audioRef.current.play().catch(() => {});
    } catch {}
  }, []);

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

  const cameraNotice = useMemo(() => "", []);

  const handleLogin = async ({ nextPatientId, nextNurseId }) => {
    setIsLoggingIn(true);
    setLoginError("");
    try {
      if (useMock) {
        const data = {
          patientId: Number(nextPatientId) || 1,
          therapistId: Number(nextNurseId) || 1,
          therapistName: "김치료사",
          name: "홍길동",
          disease_name: "뇌졸중",
          rehab_phase: "MIDDLE",
          exerciseIds: [1, 2],
        };
        setPatientId(String(data.patientId ?? nextPatientId));
        setNurseId(String(data.therapistId ?? nextNurseId));
        setTherapistName(data.therapistName ?? "");
        setPatientName(data.name ?? "");
        setDiseaseName(data.disease_name ?? "");
        setRehabPhase(data.rehab_phase ?? "");
        setExerciseIds(Array.isArray(data.exerciseIds) ? data.exerciseIds : []);
        setExerciseIndex(0);
        setScreen(SCREEN.PATIENT_CHECK);
        return;
      }
      console.log("[API] login GET", {
        url: `${API_USER_BASE_URL}/api/patients/therapists/${nextNurseId}/patients/${nextPatientId}/summary`,
      });
      const res = await fetch(
        `${API_USER_BASE_URL}/api/patients/therapists/${nextNurseId}/patients/${nextPatientId}/summary`,
        { method: "GET" }
      );
      console.log("[API] login status", res.status);
      if (!res.ok) {
        throw new Error("로그인 정보를 확인해주세요.");
      }
      const data = await res.json();
      console.log("[API] login response", data);
      setPatientId(String(data.patientId ?? nextPatientId));
      setNurseId(String(data.therapistId ?? nextNurseId));
      setTherapistName(data.therapistName ?? "");
      setPatientName(data.name ?? "");
      setDiseaseName(data.disease_name ?? "");
      setRehabPhase(data.rehab_phase ?? "");
      setExerciseIds(Array.isArray(data.exerciseIds) ? data.exerciseIds : []);
      setExerciseIndex(0);
      setScreen(SCREEN.PATIENT_CHECK);
    } catch (err) {
      setLoginError("로그인에 실패했습니다. 입력값을 확인해주세요.");
    } finally {
      setIsLoggingIn(false);
    }
  };

  const moveToExerciseIntro = () => {
    setPostureChecked(false);
    setScreen(SCREEN.EXERCISE_INTRO);
  };

  const todayExerciseIds = exerciseIds
    .map((id) => Number(id))
    .filter((id) => id in EXERCISE_CATALOG);
  const hasExercises = todayExerciseIds.length > 0;
  const todayExercises = todayExerciseIds.map((id) => EXERCISE_CATALOG[id]);
  const currentSession = sequenceSessions[exerciseIndex] ?? null;
  const currentTryIds = Array.isArray(currentSession?.tryIds) ? currentSession.tryIds : [];
  const totalTries = currentTryIds.length || 10;
  const currentExerciseId = todayExerciseIds[exerciseIndex];
  const currentExerciseDetail = currentExerciseId
    ? exerciseDetails[currentExerciseId]
    : null;
  const currentExercise = {
    title:
      currentExerciseDetail?.name ??
      todayExercises[exerciseIndex]?.title ??
      EXERCISE_CATALOG[1].title,
    instruction:
      currentExerciseDetail?.description ??
      todayExercises[exerciseIndex]?.instruction ??
      EXERCISE_CATALOG[1].instruction,
    caution:
      currentExerciseDetail?.precautions ??
      todayExercises[exerciseIndex]?.caution ??
      EXERCISE_CATALOG[1].caution,
    postureGuide:
      currentExerciseDetail?.postureGuide ??
      "카메라 화면에 팔과 어깨가 모두 보이면 자동으로 넘어갑니다.",
  };
  const sessionCount =
    currentExerciseId === 1
      ? armRaiseCount
      : currentExerciseId === 2
        ? moleGameCount
        : Math.min(tryIndex + 1, totalTries);
  const sessionTotal =
    currentExerciseId === 1
      ? armRaiseTotal
      : currentExerciseId === 2
        ? moleGameTotal
        : totalTries;
  const guideVideoSrc =
    currentExerciseId === 2 ? "/down_guide.mp4" : "/up_guide.mp4";


  const startSequence = async () => {
    if (!hasExercises) {
      setScreen(SCREEN.EXERCISE_RESULT);
      return;
    }
    const trimmedPatientId = String(patientId || "").trim();
    if (!trimmedPatientId) {
      moveToExerciseIntro();
      return;
    }
    try {
      if (useMock) {
        console.log("[FLOW] sequence start");
        setSequenceId(1);
        setSequenceSessions(
          todayExerciseIds.map((exerciseId, index) => ({
            sessionId: 100 + index,
            exerciseId,
            tryIds: Array.from({ length: 10 }, (_, i) => 1000 + index * 10 + i),
          }))
        );
        moveToExerciseIntro();
        return;
      }
      console.log("[FLOW] sequence start");
      console.log("[API] sequence POST", {
        url: `${API_USER_BASE_URL}/api/sequence/${trimmedPatientId}`,
        body: { triesPerSession: 10 },
      });
      const res = await fetch(
        `${API_USER_BASE_URL}/api/sequence/${trimmedPatientId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ triesPerSession: 10 }),
        }
      );
      console.log("[API] sequence status", res.status);
      if (!res.ok) {
        throw new Error("시퀀스 생성 실패");
      }
      const data = await res.json();
      console.log("[API] sequence response", data);
      setSequenceId(data.sequenceId ?? null);
      setSequenceSessions(Array.isArray(data.sessions) ? data.sessions : []);
      moveToExerciseIntro();
    } catch (err) {
      moveToExerciseIntro();
    }
  };

  const successCount = 8;
  const resultRule =
    RESULT_RULES.find(
      (rule) => successCount >= rule.min && successCount <= rule.max
    ) ?? RESULT_RULES[0];

  const compareTopItems = compareItems.length
    ? compareItems.slice(0, 2)
    : [
        { exerciseId: "upper", exerciseName: "상체 운동", diff: "" },
        { exerciseId: "lower", exerciseName: "하체 운동", diff: "" },
      ];
  const diffValues = compareTopItems.map((item) => Number(item.diff));
  const validDiffs = diffValues.map((value) => (Number.isFinite(value) ? value : 0));
  const focusIndex = validDiffs.length
    ? validDiffs.indexOf(Math.min(...validDiffs))
    : 0;
  const goalLines = compareTopItems.map((item, index) => {
    const diff = Number(item.diff);
    const isUp = Number.isFinite(diff) && diff > 0;
    const isDownOrSame = !Number.isFinite(diff) || diff <= 0;
    let message = isUp
      ? "지금 흐름을 편안하게 이어가볼게요."
      : "다음에는 천천히 같은 동작을 이어가볼게요.";
    if (index === focusIndex) {
      message = isUp
        ? "좋은 흐름을 유지하며 조금 더 안정적으로 이어가볼게요."
        : "이 동작은 조금 더 신경 써서 천천히 이어가볼게요.";
    }
    if (isDownOrSame && index !== focusIndex) {
      message = "무리하지 않고 편안한 속도로 진행하면 됩니다.";
    }
    return `${item.exerciseName}: ${message}`;
  });

  useEffect(() => {
    if (!hasExercises && (screen === SCREEN.EXERCISE_LIST || screen === SCREEN.EXERCISE_INTRO)) {
      setScreen(SCREEN.EXERCISE_RESULT);
    }
  }, [hasExercises, screen]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_INTRO) return;
    setPostureChecked(false);
    setGuideEnded(false);
    return undefined;
  }, [screen, exerciseIndex]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_INTRO || !guideEnded) return;
    setPostureChecked(true);
    const timeout = setTimeout(() => {
      enterSession();
    }, 200);
    return () => clearTimeout(timeout);
  }, [screen, guideEnded]);

  useEffect(() => {
    if (!currentExerciseId) return;
    if (exerciseDetails[currentExerciseId]) return;
    const fetchDetail = async () => {
      try {
        if (useMock) {
          setExerciseDetails((prev) => ({
            ...prev,
            [currentExerciseId]: {
              name: currentExerciseId === 1 ? "팔 들어올리기 운동" : "하체 힘 회복 운동",
              description:
                currentExerciseId === 1
                  ? "팔을 천천히 들어 올리고 2초 유지한 뒤 내려주세요."
                  : "하체에 힘을 주며 천천히 움직이고 균형을 유지해주세요.",
              precautions:
                currentExerciseId === 1
                  ? "어깨가 올라가지 않도록 자연스럽게 움직여주세요."
                  : "무릎이 과하게 앞으로 나가지 않도록 천천히 진행해주세요.",
              postureGuide: "카메라 화면에 팔과 어깨가 모두 보이면 자동으로 넘어갑니다.",
            },
          }));
          return;
        }
        console.log("[API] exercise detail GET", {
          url: `${API_USER_BASE_URL}/api/exercises/${currentExerciseId}`,
        });
        const res = await fetch(`${API_USER_BASE_URL}/api/exercises/${currentExerciseId}`, {
          method: "GET",
        });
        console.log("[API] exercise detail status", res.status);
        if (!res.ok) return;
        const data = await res.json();
        console.log("[API] exercise detail response", data);
        setExerciseDetails((prev) => ({
          ...prev,
          [currentExerciseId]: data,
        }));
      } catch {
        // ignore fetch errors for now
      }
    };
    fetchDetail();
  }, [currentExerciseId]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.code === 'KeyW') {
        setHoldingPower(requiredPower);
      }
    };
    const onKeyUp = (e) => {
      if (e.code === 'KeyW') {
        setHoldingPower(0);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
    };
  }, [requiredPower]);

  const preloadMoleModel = useCallback(() => {
    if (molePreloadRef.current) return;
    molePreloadRef.current = true;
    try {
      THREE.Cache.enabled = true;
      const loader = new GLTFLoader();
      loader.load(
        "/mole7.glb",
        () => {
          molePreloadRef.current = true;
        },
        undefined,
        () => {
          molePreloadRef.current = false;
        }
      );
    } catch {
      molePreloadRef.current = false;
    }
  }, []);

  const clearCountdown = useCallback(() => {
    if (countdownTimerRef.current) {
      clearTimeout(countdownTimerRef.current);
      countdownTimerRef.current = null;
    }
    countdownActiveRef.current = false;
    countdownTokenRef.current += 1;
    setCountdownStep(null);
  }, []);

  const sendSessionStartSignal = async (sessionId) => {
    if (!sessionId) return;
    if (startedSessionId === sessionId) return;
    try {
      if (useMock) {
        console.log("[FLOW] session start", sessionId);
        setStartedSessionId(sessionId);
        return;
      }
      console.log("[FLOW] session start", sessionId);
      await fetch(`${API_USER_BASE_URL}/sessions/${sessionId}/start`, {
        method: "POST",
      });
    } catch {
      // ignore start errors for now
    } finally {
      setStartedSessionId(sessionId);
    }
  };

  const enterSession = () => {
    setScreen(SCREEN.EXERCISE_SESSION);
  };

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_INTRO) return;
    const sessionId = sequenceSessions[exerciseIndex]?.sessionId;
    if (!sessionId || sessionStartSentRef.current === sessionId) return;
    sessionStartSentRef.current = sessionId;
    sendSessionStartSignal(sessionId);
    if (currentExerciseId === 2) {
      preloadMoleModel();
    }
  }, [screen, exerciseIndex, sequenceSessions, currentExerciseId, sendSessionStartSignal, preloadMoleModel]);

  const startTry = async (nextTryId) => {
    if (!nextTryId || activeTryId === nextTryId) return;
    if (startedTryRef.current === nextTryId) return;
    try {
      if (useMock) {
        console.log("[FLOW] try start", nextTryId);
        startedTryRef.current = nextTryId;
        setActiveTryId(nextTryId);
        return;
      }
      console.log("[FLOW] try start", nextTryId);
      startedTryRef.current = nextTryId;
      console.log("[API] try start", {
        url: `${API_USER_BASE_URL}/api/tries/${nextTryId}/start`,
      });
      await fetch(`${API_USER_BASE_URL}/api/tries/${nextTryId}/start`, { method: "POST" });
    } catch {
      // ignore start errors for now
    } finally {
      setActiveTryId(nextTryId);
    }
  };

  const runCountdown = useCallback((nextTryId) => {
    if (!nextTryId) return;
    if (startedTryRef.current === nextTryId) return;
    clearCountdown();
    countdownActiveRef.current = true;
    const token = countdownTokenRef.current + 1;
    countdownTokenRef.current = token;
    const steps = ["3", "2", "1", "시작"];
    let index = 0;
    playFailAudio(steps[index]);
    setCountdownStep(steps[index]);
    const tick = () => {
      if (countdownTokenRef.current !== token) return;
      index += 1;
      if (index < steps.length) {
        playFailAudio(steps[index]);
        setCountdownStep(steps[index]);
        if (index === steps.length - 1) {
          startTry(nextTryId);
          countdownTimerRef.current = setTimeout(() => {
            if (countdownTokenRef.current !== token) return;
            clearCountdown();
            if (currentExerciseId === 2) {
              setMoleTrySignal((prev) => prev + 1);
            }
          }, 1000);
          return;
        }
        countdownTimerRef.current = setTimeout(tick, 1000);
      }
    };
    countdownTimerRef.current = setTimeout(tick, 1000);
  }, [clearCountdown, startTry, currentExerciseId]);

  const finishTry = async (nextTryId) => {
    if (!nextTryId) return;
    try {
      if (useMock) {
        console.log("[FLOW] try finish", nextTryId);
        setTryScores((prev) => ({ ...prev, [nextTryId]: 10 }));
        return;
      }
      console.log("[FLOW] try finish", nextTryId);
      console.log("[API] try finish", {
        url: `${API_USER_BASE_URL}/api/tries/${nextTryId}/finish`,
        body: { tryId: nextTryId, failType: "", totalScore: 0 },
      });
      const res = await fetch(`${API_USER_BASE_URL}/api/tries/${nextTryId}/finish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tryId: nextTryId,
        }),
      });
      console.log("[API] try finish status", res.status);
      if (res.ok) {
        const data = await res.json();
        console.log("[API] try finish response", data);
        if (typeof data?.totalScore === "number") {
          setTryScores((prev) => ({ ...prev, [nextTryId]: data.totalScore }));
        }
        return data;
      }
    } catch {
      // ignore finish errors for now
    }
    startedTryRef.current = null;
    return null;
  };

  const finishSession = async () => {
    const sessionId = sequenceSessions[exerciseIndex]?.sessionId;
    if (!sessionId) return;
    try {
      if (useMock) {
        console.log("[FLOW] session finish", sessionId);
        return;
      }
      console.log("[FLOW] session finish", sessionId);
      console.log("[API] session finish", {
        url: `${API_USER_BASE_URL}/api/sessions/${sessionId}/finish`,
      });
      await fetch(`${API_USER_BASE_URL}/api/sessions/${sessionId}/finish`, {
        method: "POST",
      });
    } catch {
      // ignore finish errors for now
    }
  };

  const finishSequence = async () => {
    if (!sequenceId) return;
    try {
      if (useMock) {
        console.log("[FLOW] sequence finish", sequenceId);
        return;
      }
      console.log("[FLOW] sequence finish", sequenceId);
      console.log("[API] sequence finish", {
        url: `${API_USER_BASE_URL}/api/sequences/${sequenceId}/finish`,
      });
      await fetch(`${API_USER_BASE_URL}/api/sequences/${sequenceId}/finish`, {
        method: "POST",
      });
    } catch {
      // ignore finish errors for now
    }
  };

  const goToNextStep = useCallback(async (options = {}) => {
    const { forceComplete = false, skipTryFinish = false } = options;
    if (currentExerciseId === 2 && moleGameCount < moleGameTotal) {
      return;
    }
    const currentTryId = currentTryIds[tryIndex];
    if (!skipTryFinish && currentTryId) {
      await finishTry(currentTryId);
    }
    if (!forceComplete && tryIndex < totalTries - 1) {
      setTryIndex((prev) => prev + 1);
      return;
    }
    await finishSession();
    if (exerciseIndex < todayExercises.length - 1) {
      setExerciseIndex((prev) => prev + 1);
      setScreen(SCREEN.EXERCISE_INTRO);
    } else {
      await finishSequence();
      setScreen(SCREEN.EXERCISE_RESULT);
    }
  }, [
    currentExerciseId,
    moleGameCount,
    moleGameTotal,
    currentTryIds,
    tryIndex,
    totalTries,
    finishTry,
    finishSession,
    finishSequence,
    exerciseIndex,
    todayExercises.length,
  ]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION) {
      if (exerciseCompleteTimerRef.current) {
        clearTimeout(exerciseCompleteTimerRef.current);
        exerciseCompleteTimerRef.current = null;
      }
      if (lowerBodyFeedbackTimerRef.current) {
        clearTimeout(lowerBodyFeedbackTimerRef.current);
        lowerBodyFeedbackTimerRef.current = null;
      }
      setExerciseCompleteFeedback(null);
      setLowerBodyFeedback(null);
      return;
    }
  }, [screen]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION || currentExerciseId !== 1) {
      autoAdvanceRef.current = false;
      armRaiseCompleteRef.current = false;
      if (armRaiseCompleteTimerRef.current) {
        clearTimeout(armRaiseCompleteTimerRef.current);
        armRaiseCompleteTimerRef.current = null;
      }
      return;
    }
    if (!armRaiseTotal) return;
    if (armRaiseCount >= armRaiseTotal && !autoAdvanceRef.current) {
      autoAdvanceRef.current = true;
      armRaiseCompleteRef.current = true;
      setArmRaiseFeedback({
        id: Date.now(),
        message: "수고하셨습니다",
        duration: 5000,
      });
      if (armRaiseCompleteTimerRef.current) {
        clearTimeout(armRaiseCompleteTimerRef.current);
      }
      if (exerciseCompleteTimerRef.current) {
        clearTimeout(exerciseCompleteTimerRef.current);
      }
      exerciseCompleteTimerRef.current = setTimeout(() => {
        goToNextStep({ forceComplete: true, skipTryFinish: true });
        exerciseCompleteTimerRef.current = null;
      }, 5000);
    }
  }, [screen, currentExerciseId, armRaiseCount, armRaiseTotal, goToNextStep]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION || currentExerciseId !== 2) {
      moleAutoAdvanceRef.current = false;
      return;
    }
    if (!moleGameTotal) return;
    if (moleGameCount >= moleGameTotal && !moleAutoAdvanceRef.current) {
      moleAutoAdvanceRef.current = true;
      setExerciseCompleteFeedback({
        id: Date.now(),
        message: "수고하셨습니다",
        duration: 5000,
      });
      if (exerciseCompleteTimerRef.current) {
        clearTimeout(exerciseCompleteTimerRef.current);
      }
      exerciseCompleteTimerRef.current = setTimeout(() => {
        goToNextStep({ forceComplete: true, skipTryFinish: true });
        exerciseCompleteTimerRef.current = null;
      }, 5000);
    }
  }, [screen, currentExerciseId, moleGameCount, moleGameTotal, goToNextStep]);

  // 하체 전용일 때도 화면 흐름은 항상 intro -> session 순서를 유지한다.

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION || currentExerciseId !== 2) {
      return;
    }
    if (useMock) {
      setSensorPower(null);
    }
  }, [screen, currentExerciseId, useMock]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_INTRO || !postureChecked) return;
    const timeout = setTimeout(() => {
      enterSession();
    }, 1200);
    return () => clearTimeout(timeout);
  }, [screen, postureChecked]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION || currentExerciseId !== 1) {
      lastArmRaiseCountRef.current = armRaiseCount;
      if (armRaiseTimeoutRef.current) {
        clearTimeout(armRaiseTimeoutRef.current);
        armRaiseTimeoutRef.current = null;
      }
      return;
    }
    if (armRaiseCount <= lastArmRaiseCountRef.current) return;
    lastArmRaiseCountRef.current = armRaiseCount;

    const run = async () => {
      let nextDelayMs = 0;
      const currentTryId = currentTryIds[tryIndex];
      startedTryRef.current = null;
      if (currentTryId) {
        const result = await finishTry(currentTryId);
        if (result && typeof result === "object") {
          const status = String(result.resultStatus || "").toUpperCase();
          if (status === "SUCCESS") {

            playFailAudio("SUCCESS");

            setArmRaiseFeedback({
              id: Date.now(),
              message: "잘하셨어요!",
              duration: 2500,
            });
            nextDelayMs = 2500;
          } else if (status === "FAIL") {
            const failId = result.failId || "F_ELSE";

            playFailAudio(failId);

            setArmRaiseFeedback({
              id: Date.now(),
              message: result.failName || "예외 발생 예외 발생",
              duration: 3500,
            });
            nextDelayMs = 3500;
          }
        }
      }

      if (armRaiseCount < armRaiseTotal) {
        if (armRaiseTimeoutRef.current) {
          clearTimeout(armRaiseTimeoutRef.current);
        }
        armRaiseTimeoutRef.current = setTimeout(() => {
          startedTryRef.current = null;
          setTryIndex((prev) => prev + 1);
          armRaiseTimeoutRef.current = null;
        }, nextDelayMs);
      }
    };

    run();
  }, [
    screen,
    currentExerciseId,
    armRaiseCount,
    armRaiseTotal,
    currentTryIds,
    tryIndex,
    finishTry,
    playFailAudio,
  ]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION || currentExerciseId !== 2) {
      lastMoleCountRef.current = moleGameCount;
      if (moleTryTimeoutRef.current) {
        clearTimeout(moleTryTimeoutRef.current);
        moleTryTimeoutRef.current = null;
      }
      return;
    }
    if (moleGameCount <= lastMoleCountRef.current) return;
    lastMoleCountRef.current = moleGameCount;
    const currentTryId = currentTryIds[tryIndex];
    const run = async () => {
      let nextDelayMs = 2500;
      if (currentTryId) {
        const result = await finishTry(currentTryId);
        if (result && typeof result === "object") {
          const status = String(result.resultStatus || "").toUpperCase();
          if (status === "SUCCESS") {
            playFailAudio("SUCCESS");
            setLowerBodyFeedback({
              id: Date.now(),
              message: "잘하셨어요!",
              duration: 2500,
            });
            nextDelayMs = 2500;
          } else if (status === "FAIL") {
            const failId = result.failId || "F_ELSE";
            playFailAudio(failId);
            setLowerBodyFeedback({
              id: Date.now(),
              message: result.failName || "예외 발생",
              duration: 3500,
            });
            nextDelayMs = 3500;
          }
        }
      }
      if (moleGameCount < moleGameTotal) {
        if (moleTryTimeoutRef.current) {
          clearTimeout(moleTryTimeoutRef.current);
        }
        if (lowerBodyFeedbackTimerRef.current) {
          clearTimeout(lowerBodyFeedbackTimerRef.current);
        }
        lowerBodyFeedbackTimerRef.current = setTimeout(() => {
          setLowerBodyFeedback(null);
          lowerBodyFeedbackTimerRef.current = null;
        }, nextDelayMs);
        moleTryTimeoutRef.current = setTimeout(() => {
          startedTryRef.current = null;
          setTryIndex((prev) => prev + 1);
          moleTryTimeoutRef.current = null;
        }, nextDelayMs);
      }
    };
    run();
  }, [
    screen,
    currentExerciseId,
    moleGameCount,
    moleGameTotal,
    currentTryIds,
    tryIndex,
    finishTry,
  ]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION) return;
    setSetIndex(1);
  }, [screen, exerciseIndex]);

  useEffect(() => {
    setStartedSessionId(null);
    setTryIndex(0);
    setActiveTryId(null);
  }, [exerciseIndex]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION) {
      lastCountdownTryRef.current = null;
      lastStartedTryIndexRef.current = -1;
      startedTryRef.current = null;
      clearCountdown();
      return;
    }
    if (!guideEnded) return;
    const nextTryId = currentTryIds[tryIndex];
    if (!nextTryId) return;
    if (lastStartedTryIndexRef.current === tryIndex) return;
    if (lastCountdownTryRef.current === nextTryId) return;
    lastCountdownTryRef.current = nextTryId;
    lastStartedTryIndexRef.current = tryIndex;
    runCountdown(nextTryId);
    if (currentExerciseId === 2) {
      preloadMoleModel();
    }
  }, [
    screen,
    guideEnded,
    tryIndex,
    currentTryIds,
    currentExerciseId,
    runCountdown,
    clearCountdown,
    preloadMoleModel,
  ]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_SESSION || currentExerciseId !== 1) {
      prevTryIndexRef.current = tryIndex;
      return;
    }
    prevTryIndexRef.current = tryIndex;
  }, [screen, currentExerciseId, tryIndex]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_RESULT || !sequenceId || !patientId) return;
    const fetchCompare = async () => {
      try {
        if (useMock) {
          setCompareItems([
            { exerciseId: "upper", exerciseName: "상체 운동", diff: "6" },
            { exerciseId: "lower", exerciseName: "하체 운동", diff: "-3" },
          ]);
          return;
        }
        console.log("[API] compare-previous GET", {
          url: `${API_USER_BASE_URL}/api/sequences/${patientId}/${sequenceId}/compare-previous`,
        });
        const res = await fetch(
          `${API_USER_BASE_URL}/api/sequences/${patientId}/${sequenceId}/compare-previous`,
          { method: "GET" }
        );
        console.log("[API] compare-previous status", res.status);
        if (!res.ok) return;
        const data = await res.json();
        console.log("[API] compare-previous response", data);
        setCompareItems(Array.isArray(data?.items) ? data.items : []);
      } catch {
        setCompareItems([]);
      }
    };
    fetchCompare();
  }, [screen, sequenceId, patientId]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_RESULT || !sequenceId || !patientId) return;
    const fetchRecentGoals = async () => {
      try {
        if (useMock) {
          setRecentGoals([
            { exerciseId: 1, goals: [8, 7, 6, 7, 8] },
            { exerciseId: 2, goals: [5, 6, 6, 7, 7] },
          ]);
          return;
        }
        console.log("[API] recent goals GET", {
          url: `${API_USER_BASE_URL}/api/sequences/${patientId}/${sequenceId}/goals/recent`,
        });
        const res = await fetch(
          `${API_USER_BASE_URL}/api/sequences/${patientId}/${sequenceId}/goals/recent`,
          { method: "GET" }
        );
        console.log("[API] recent goals status", res.status);
        if (!res.ok) return;
        const data = await res.json();
        console.log("[API] recent goals response", data);
        setRecentGoals(Array.isArray(data?.items) ? data.items : []);
      } catch {
        setRecentGoals([]);
      }
    };
    fetchRecentGoals();
  }, [screen, sequenceId, patientId]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_RESULT || !sequenceId) return;
    const fetchAverages = async () => {
      try {
        if (useMock) {
          setSequenceAverages([
            { exerciseId: 1, totalTries: 12, successTries: 10 },
            { exerciseId: 2, totalTries: 12, successTries: 8 },
          ]);
          return;
        }
        console.log("[API] sequence averages GET", {
          url: `${API_USER_BASE_URL}/api/sequence/${sequenceId}/average`,
        });
        const res = await fetch(`${API_USER_BASE_URL}/api/sequence/${sequenceId}/average`, {
          method: "GET",
        });
        console.log("[API] sequence averages status", res.status);
        if (!res.ok) return;
        const data = await res.json();
        console.log("[API] sequence averages response", data);
        setSequenceAverages(Array.isArray(data) ? data : []);
      } catch {
        setSequenceAverages([]);
      }
    };
    fetchAverages();
  }, [screen, sequenceId]);

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
      cameraNotice={cameraNotice || undefined}
    >
      {screen === SCREEN.LOGIN && (
        <Login
          onSubmit={handleLogin}
          isLoading={isLoggingIn}
          errorMessage={loginError}
        />
      )}
      {screen === SCREEN.PATIENT_CHECK && (
        <PatientCheck
          onStart={() => {
            setExerciseIndex(0);
            setScreen(hasExercises ? SCREEN.EXERCISE_LIST : SCREEN.EXERCISE_RESULT);
          }}
          onBack={() => setScreen(SCREEN.LOGIN)}
          patientId={patientId}
          patientName={patientName}
          diseaseName={diseaseName}
          rehabPhase={rehabPhase}
          exerciseIds={exerciseIds}
        />
      )}
      {screen === SCREEN.EXERCISE_LIST && (
        <div className="placeholder-screen enter">
          <div className="screen-label">오늘의 운동</div>
          <h1>오늘의 재활 운동</h1>
          <p className="lead">
            오늘 해야 할 {todayExercises.length}가지 동작이 준비되어 있습니다.
          </p>
          {todayExercises.map((exercise, index) => (
            <div
              key={`${exercise.title}-${index}`}
              className={`placeholder-card${index === 0 ? "" : " muted"}`}
            >
              <div>
                <div className="card-title">
                  {index + 1}. {exercise.title}
                </div>
                <div className="card-meta">{exercise.duration}</div>
              </div>
              <span className={`card-badge${index === 0 ? "" : " subtle"}`}>
                {index === 0 ? "대표 동작" : "대기"}
              </span>
            </div>
          ))}
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
              onClick={startSequence}
              disabled={!hasExercises}
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
                <div className="card-meta">{currentExercise.caution}</div>
              </div>
            </div>
          </div>
          <div className="check-row">
            <div>
              <div className="card-title">자세 확인</div>
              <div className="card-meta">
                {currentExercise.postureGuide}
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
              ? "인식 완료. 곧 운동이 시작됩니다."
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
              onClick={enterSession}
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
            {!guideEnded && (
              <div className="exercise-guide-video">
                <video
                  src={guideVideoSrc}
                  autoPlay
                  playsInline
                  onEnded={() => setGuideEnded(true)}
                  controls={false}
                />
              </div>
            )}
            {exerciseCompleteFeedback && exerciseCompleteFeedback.message && (
              <div className="arm-raise-feedback" style={{ opacity: 1 }}>
                {exerciseCompleteFeedback.message}
              </div>
            )}
            {currentExerciseId === 2 &&
              lowerBodyFeedback &&
              lowerBodyFeedback.message && (
                <div className="arm-raise-feedback" style={{ opacity: 1 }}>
                  {lowerBodyFeedback.message}
                </div>
              )}
            {countdownStep && (
              <div className="try-countdown-overlay">
                <div className="try-countdown-text">{countdownStep}</div>
              </div>
            )}
            {guideEnded && currentExerciseId === 2 ? (
              <MoleGame
                onCountChange={(count, total) => {
                  setMoleGameCount(count);
                  setMoleGameTotal(total);
                }}
                onPowerChange={(power) => setSensorPower(power)}
                requiredPower={requiredPower}
                tryStartSignal={moleTrySignal}
                showLoadingOverlay={false}
              />
            ) : guideEnded ? (
              <ArmRaiseGame
                onCountChange={(count, total) => {
                  setArmRaiseCount(count);
                  setArmRaiseTotal(total);
                }}
                resultFeedback={armRaiseFeedback}
              />
            ) : null}
          </div>
          <div className="session-panel session-panel-next">
            {currentExerciseId === 2 && (
              <div className="power-gauge">
                <div className="power-gauge-track">
                  <span
                    className="power-gauge-fill"
                    style={{
                      width: `${
                        requiredPower > 0
                          ? Math.min(((holdingPower || sensorPower || 0) / requiredPower) * 100, 100)
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
            )}
            <div className="session-bar">
              <span
                style={{
                  width: `${
                    sessionTotal ? (Math.min(sessionCount, sessionTotal) / sessionTotal) * 100 : 0
                  }%`,
                }}
              />
            </div>
            <div className="card-meta">
              현재 {Math.min(sessionCount, sessionTotal)}/{sessionTotal} 회
            </div>
          </div>
          <button
            className="ghost-button session-next"
            type="button"
            onClick={() => {
              if (screen === SCREEN.EXERCISE_SESSION && currentExerciseId === 1) {
                if (armRaiseCount < armRaiseTotal) {
                  setArmRaiseCount((prev) => Math.min(prev + 1, armRaiseTotal));
                  if (tryIndex < totalTries - 1) {
                    setTryIndex((prev) => prev + 1);
                  }
                  return;
                }
              }
              if (screen === SCREEN.EXERCISE_SESSION && currentExerciseId === 2) {
                if (moleGameCount < moleGameTotal) {
                  setMoleGameCount((prev) => Math.min(prev + 1, moleGameTotal));
                  if (tryIndex < totalTries - 1) {
                    setTryIndex((prev) => prev + 1);
                  }
                  return;
                }
                if (moleGameCount >= moleGameTotal) {
                  goToNextStep({ forceComplete: true, skipTryFinish: true });
                  return;
                }
              }
              goToNextStep();
            }}
          >
            다음 단계
          </button>
        </div>
      )}
      {screen === SCREEN.EXERCISE_RESULT && (
        <div className="placeholder-screen result-screen enter">
          {(() => {
            const performedIds = Array.from(new Set(todayExerciseIds));
            const averages = sequenceAverages.length ? sequenceAverages : [];
            const upper =
              averages.find((item) => Number(item.exerciseId) === 1) ??
              (performedIds.includes(1)
                ? { exerciseId: 1, totalTries: 0, successTries: 0 }
                : null);
            const lower =
              averages.find((item) => Number(item.exerciseId) === 2) ??
              (performedIds.includes(2)
                ? { exerciseId: 2, totalTries: 0, successTries: 0 }
                : null);
            const upperGoals =
              recentGoals.find((item) => Number(item.exerciseId) === 1)?.goals ?? [];
            const lowerGoals =
              recentGoals.find((item) => Number(item.exerciseId) === 2)?.goals ?? [];
            const goalLength = Math.max(
              performedIds.includes(1) ? upperGoals.length : 0,
              performedIds.includes(2) ? lowerGoals.length : 0,
              0
            );
            const chartData = Array.from({ length: Math.max(goalLength, 5) }).map(
              (_, index) => ({
                name: `${index + 1}`,
                ...(performedIds.includes(1)
                  ? { upper: Number(upperGoals[index] ?? 0) }
                  : {}),
                ...(performedIds.includes(2)
                  ? { lower: Number(lowerGoals[index] ?? 0) }
                  : {}),
              })
            );
            return (
          <div className="result-layout">
            <section className="result-left">
              <div className="result-left-inner">
                <div className="screen-label">운동 결과</div>
                <div className="result-title-row">
                  <h1>오늘의 기록</h1>
                  {hasExercises && (
                    <div className="result-toggles">
                      <span className="result-toggle upper">상체</span>
                      <span className="result-toggle lower">하체</span>
                    </div>
                  )}
                </div>
                {!hasExercises && (
                  <div className="info-grid single result-cards">
                    <div className="info-card accent">
                      <div>
                        <div className="card-title">금일 운동이 없습니다</div>
                        <div className="card-meta">
                          오늘은 휴식이 필요한 날이에요. 다음 일정에 맞춰 다시 시작해요.
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                {hasExercises && (
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
                          {(compareItems.length ? compareItems.slice(0, 2) : [
                            { exerciseId: "upper", exerciseName: "상체 운동", diff: "" },
                            { exerciseId: "lower", exerciseName: "하체 운동", diff: "" },
                          ]).map((item, index) => {
                            const parsedDiff = Number(item.diff);
                            const isValid = Number.isFinite(parsedDiff);
                            const absDiff = Math.abs(parsedDiff);
                            const isUp = parsedDiff > 0;
                            const isDown = parsedDiff < 0;
                            let level = "";
                            if (!isValid || absDiff === 0) {
                              level = "오늘도 안정적으로 이어가고 있어요";
                            } else if (absDiff <= 5) {
                              level = isUp
                                ? "조금 더 편안하게 움직일 수 있었어요"
                                : "천천히 조절해도 괜찮아요";
                            } else if (absDiff <= 10) {
                              level = isUp
                                ? "움직임이 전보다 자연스러워졌어요"
                                : "리듬을 천천히 맞춰가고 있어요";
                            } else if (absDiff <= 15) {
                              level = isUp
                                ? "움직임이 안정적으로 이어졌어요"
                                : "무리하지 않고 진행해도 충분해요";
                            } else if (absDiff <= 20) {
                              level = isUp
                                ? "오늘은 움직임이 꽤 부드러웠어요"
                                : "오늘은 몸을 풀어주는 데 집중했어요";
                            } else if (absDiff <= 25) {
                              level = isUp
                                ? "오늘은 동작을 편안하게 잘 이어갔어요"
                                : "컨디션에 맞춰 천천히 진행했어요";
                            } else if (absDiff <= 30) {
                              level = isUp
                                ? "움직임 흐름이 한층 더 자연스러워졌어요"
                                : "오늘은 몸을 쉬어가며 진행했어요";
                            } else {
                              level = isUp
                                ? "오늘은 움직임이 아주 편안했어요"
                                : "오늘은 몸 상태를 살피며 진행했어요";
                            }
                            const detail = "";
                            return (
                              <div
                                key={item.exerciseId ?? index}
                                className={`change-item ${index === 0 ? "upper" : "lower"}`}
                              >
                                {item.exerciseName}: {level}{detail}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                    <div className="info-card">
                      <div>
                        <div className="card-title">앞으로의 목표</div>
                        <div className="card-meta goal-change-list">
                          {goalLines.map((line, index) => (
                            <div
                              key={line}
                              className={`change-item ${index === 0 ? "upper" : "lower"}`}
                            >
                              {line}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>
            {hasExercises && (
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
                    {upper && (
                      <div className="donut-item">
                        <div className="donut-chart">
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={[
                                  { name: "성공", value: upper.successTries },
                                  { name: "나머지", value: Math.max(upper.totalTries - upper.successTries, 0) },
                                ]}
                                dataKey="value"
                                innerRadius={58}
                                outerRadius={90}
                                paddingAngle={2}
                              >
                                <Cell fill="#b56a6a" />
                                <Cell fill="#e6dfd6" />
                              </Pie>
                            </PieChart>
                          </ResponsiveContainer>
                          <div className="donut-center">
                            <div className="donut-value">
                              {upper.successTries}/{upper.totalTries}
                            </div>
                          </div>
                          <div className="donut-label donut-label-float">
                            <span className="legend-dot upper" />
                            상체 성공
                          </div>
                        </div>
                      </div>
                    )}
                    {lower && (
                      <div className="donut-item">
                        <div className="donut-chart">
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={[
                                  { name: "성공", value: lower.successTries },
                                  { name: "나머지", value: Math.max(lower.totalTries - lower.successTries, 0) },
                                ]}
                                dataKey="value"
                                innerRadius={58}
                                outerRadius={90}
                                paddingAngle={2}
                              >
                                <Cell fill="#6f8fb8" />
                                <Cell fill="#e6dfd6" />
                              </Pie>
                            </PieChart>
                          </ResponsiveContainer>
                          <div className="donut-center">
                            <div className="donut-value">
                              {lower.successTries}/{lower.totalTries}
                            </div>
                          </div>
                          <div className="donut-label donut-label-float">
                            <span className="legend-dot lower" />
                            하체 성공
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="chart-card">
                  <div className="card-title">최근 5번 정확도 추이</div>
                  <div className="chart-area">
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={chartData}>
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip />
                        {performedIds.includes(1) && (
                          <Line
                            type="monotone"
                            dataKey="upper"
                            stroke="#b56a6a"
                            strokeWidth={3}
                            dot={{ r: 4 }}
                          />
                        )}
                        {performedIds.includes(2) && (
                          <Line
                            type="monotone"
                            dataKey="lower"
                            stroke="#6f8fb8"
                            strokeWidth={3}
                            dot={{ r: 4 }}
                          />
                        )}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </section>
            )}
          </div>
            );
          })()}
        </div>
      )}
    </MainLayout>
  );
}



