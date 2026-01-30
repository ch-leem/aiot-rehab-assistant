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
  const [moleGameCount, setMoleGameCount] = useState(0);
  const [moleGameTotal, setMoleGameTotal] = useState(10);
  const autoAdvanceRef = useRef(false);
  const moleAutoAdvanceRef = useRef(false);
  const armRaiseTimeoutRef = useRef(null);
  const lastArmRaiseCountRef = useRef(0);
  const armRaiseCompleteRef = useRef(false);
  const prevTryIndexRef = useRef(0);
  const [activeTryId, setActiveTryId] = useState(null);
  const [compareItems, setCompareItems] = useState([]);
  const [sequenceAverages, setSequenceAverages] = useState([]);
  const [recentGoals, setRecentGoals] = useState([]);
  const [tryScores, setTryScores] = useState({});

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

  const cameraNotice = useMemo(() => {
    if (screen === SCREEN.PATIENT_CHECK) {
      return "카메라 화면에 팔과 어깨가 모두 보이도록 앉아주세요.";
    }
    if (screen === SCREEN.EXERCISE_INTRO && !postureChecked) {
      return "카메라 화면에 팔과 어깨가 모두 보이면 자동으로 넘어갑니다.";
    }
    return "";
  }, [screen, postureChecked]);

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
    const timeout = setTimeout(() => {
      setPostureChecked(true);
    }, 6000);
    return () => clearTimeout(timeout);
  }, [screen, exerciseIndex]);

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

  const startSession = async () => {
    const sessionId = sequenceSessions[exerciseIndex]?.sessionId;
    if (!sessionId || startedSessionId === sessionId) {
      setScreen(SCREEN.EXERCISE_SESSION);
      return;
    }
    try {
      if (useMock) {
        setStartedSessionId(sessionId);
        setScreen(SCREEN.EXERCISE_SESSION);
        return;
      }
      console.log("[API] session start", {
        url: `${API_USER_BASE_URL}/sessions/${sessionId}/start`,
      });
      await fetch(`${API_USER_BASE_URL}/sessions/${sessionId}/start`, {
        method: "POST",
      });
    } catch {
      // ignore start errors for now
    } finally {
      setStartedSessionId(sessionId);
      setScreen(SCREEN.EXERCISE_SESSION);
    }
  };

  const startTry = async (nextTryId) => {
    if (!nextTryId || activeTryId === nextTryId) return;
    try {
      if (useMock) {
        setActiveTryId(nextTryId);
        return;
      }
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

  const finishTry = async (nextTryId) => {
    if (!nextTryId) return;
    try {
      if (useMock) {
        setTryScores((prev) => ({ ...prev, [nextTryId]: 10 }));
        return;
      }
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
    return null;
  };

  const finishSession = async () => {
    const sessionId = sequenceSessions[exerciseIndex]?.sessionId;
    if (!sessionId) return;
    try {
      if (useMock) return;
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
      if (useMock) return;
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
    if (screen !== SCREEN.EXERCISE_SESSION || currentExerciseId !== 1) {
      autoAdvanceRef.current = false;
      armRaiseCompleteRef.current = false;
      return;
    }
    if (!armRaiseTotal) return;
    if (armRaiseCount >= armRaiseTotal && !autoAdvanceRef.current) {
      autoAdvanceRef.current = true;
      armRaiseCompleteRef.current = true;
      setArmRaiseFeedback({
        id: Date.now(),
        message: "고생하셨습니다.\n오늘도 완료하셨습니다",
        duration: 5000,
      });
      setTimeout(() => {
        goToNextStep({ forceComplete: true, skipTryFinish: true });
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
      goToNextStep({ forceComplete: true, skipTryFinish: true });
    }
  }, [screen, currentExerciseId, moleGameCount, moleGameTotal, goToNextStep]);

  useEffect(() => {
    if (screen !== SCREEN.EXERCISE_INTRO || !postureChecked) return;
    const timeout = setTimeout(() => {
      startSession();
    }, 1200);
    return () => clearTimeout(timeout);
  }, [screen, postureChecked, exerciseIndex, sequenceSessions, startedSessionId]);

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
      let nextDelayMs = 2000;
      const currentTryId = currentTryIds[tryIndex];
      if (currentTryId) {
        const result = await finishTry(currentTryId);
        if (result && typeof result === "object") {
          const status = String(result.resultStatus || "").toUpperCase();
          if (status === "SUCCESS") {
            setArmRaiseFeedback({
              id: Date.now(),
              message: "잘하셨어요!",
              duration: 2000,
            });
            nextDelayMs = 2000;
          } else if (status === "FAIL") {
            setArmRaiseFeedback({
              id: Date.now(),
              message: result.failId || "팔 높이를 더 올려주세요",
              duration: 2400,
            });
            nextDelayMs = 2400;
          }
        }
      }

      if (armRaiseCount < armRaiseTotal) {
        if (armRaiseTimeoutRef.current) {
          clearTimeout(armRaiseTimeoutRef.current);
        }
        armRaiseTimeoutRef.current = setTimeout(() => {
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
    if (screen !== SCREEN.EXERCISE_SESSION) return;
    const nextTryId = currentTryIds[tryIndex];
    if (nextTryId) {
      startTry(nextTryId);
    }
  }, [screen, tryIndex, currentTryIds]);

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
              onClick={startSession}
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
            {currentExerciseId === 1 ? (
              <ArmRaiseGame
                onCountChange={(count, total) => {
                  setArmRaiseCount(count);
                  setArmRaiseTotal(total);
                }}
                resultFeedback={armRaiseFeedback}
              />
            ) : currentExerciseId === 2 ? (
              <MoleGame
                onCountChange={(count, total) => {
                  setMoleGameCount(count);
                  setMoleGameTotal(total);
                }}
              />
            ) : (
              <div className="session-visual-placeholder">3D 반응형 화면 자리</div>
            )}
          </div>
          <div className="session-panel session-panel-next">
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
            onClick={goToNextStep}
          >
            다음 단계
          </button>
        </div>
      )}
      {screen === SCREEN.EXERCISE_RESULT && (
        <div className="placeholder-screen result-screen enter">
          {(() => {
            const defaults = [
              { exerciseId: 1, totalTries: 12, successTries: 10 },
              { exerciseId: 2, totalTries: 12, successTries: 8 },
            ];
            const averages = sequenceAverages.length ? sequenceAverages : defaults;
            const upper =
              averages.find((item) => Number(item.exerciseId) === 1) ?? defaults[0];
            const lower =
              averages.find((item) => Number(item.exerciseId) === 2) ?? defaults[1];
            const upperFill = upper.totalTries
              ? Math.round((upper.successTries / upper.totalTries) * 100)
              : 0;
            const lowerFill = lower.totalTries
              ? Math.round((lower.successTries / lower.totalTries) * 100)
              : 0;
            const upperGoals =
              recentGoals.find((item) => Number(item.exerciseId) === 1)?.goals ?? [];
            const lowerGoals =
              recentGoals.find((item) => Number(item.exerciseId) === 2)?.goals ?? [];
            const goalLength = Math.max(upperGoals.length, lowerGoals.length, 5);
            const chartData = Array.from({ length: goalLength }).map((_, index) => ({
              name: `${index + 1}`,
              upper: Number(upperGoals[index] ?? 0),
              lower: Number(lowerGoals[index] ?? 0),
            }));
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
                        <Line
                          type="monotone"
                          dataKey="upper"
                          stroke="#b56a6a"
                          strokeWidth={3}
                          dot={{ r: 4 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="lower"
                          stroke="#6f8fb8"
                          strokeWidth={3}
                          dot={{ r: 4 }}
                        />
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



