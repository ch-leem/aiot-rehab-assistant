import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DetailCharts, { FooterTimeline } from "./fail3d/Timeline";
import Pose3D from "./fail3d/Pose3D";
import JointPanel from "./fail3d/JointPanel";
import "./TherapistFail3D.css";

const normalizeApiBase = (value) => (value ?? "").replace(/\/+$/g, "");
const API_IOT_BASE_URL = normalizeApiBase(import.meta.env.VITE_API_IOT_BASE_URL);

const clamp = (v, mn, mx) => Math.max(mn, Math.min(mx, v));

const FAIL_LABEL_MAP = {
  F_SH_FLEX: "어깨 외전 각도 미달",
  F_EL_EXT: "팔꿈치 신전 불량",
  F_TR_TILT: "상체 기울기 불안정",
  F_SH_HOR: "어깨 수평 불균형",
  F_ACCEL: "수행 속도 급격",
  F_PR_LOAD: "마비측 압력 부족",
  F_PL_HOR: "골반 수평 편차",
  F_ANK_STB: "발목 흔들림 심함",
  F_ELSE: "기타 실패",
};

function estimatePeriodMs(frames) {
  if (frames.length < 2) return 33;
  const t0 = Number(frames[0]?.ts?.video_ms ?? 0);
  const tN = Number(frames[frames.length - 1]?.ts?.video_ms ?? 0);
  const span = tN - t0;
  const avg = span / (frames.length - 1);
  return avg > 0 ? avg : 33;
}

function normalizeFrames(payload) {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.frames)) return payload.frames;
  if (Array.isArray(payload.data?.frames)) return payload.data.frames;
  return [];
}

function parseJsonlText(text) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  const parsed = lines.map((line, idx) => {
    try {
      return JSON.parse(line);
    } catch (err) {
      throw new Error(`JSONL 파싱 실패: ${idx + 1}번째 줄`);
    }
  });

  const flattened = [];
  parsed.forEach((item) => {
    if (item && typeof item === "object") {
      if (Array.isArray(item.frames)) {
        item.frames.forEach((frame) => flattened.push(frame));
        return;
      }
      if ("frame_idx" in item && "ts" in item) {
        flattened.push(item);
        return;
      }
    }
    flattened.push(item);
  });

  const frames = normalizeFrames({ frames: flattened });
  if (frames.length > 0) return frames;
  return normalizeFrames(flattened);
}

function parseAnyText(text) {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const payload = JSON.parse(trimmed);
      const normalized = normalizeFrames(payload);
      if (normalized.length > 0) return normalized;
    } catch {
      // fall back to JSONL parsing
    }
  }
  return parseJsonlText(text);
}

function extractFramesFromPayload(payload) {
  if (!payload) return [];
  const normalized = normalizeFrames(payload);
  if (normalized.length > 0) return normalized;
  const inlineFrames = payload?.data?.frames ?? payload?.frames;
  if (Array.isArray(inlineFrames)) {
    const flattened = [];
    inlineFrames.forEach((item) => {
      if (item && typeof item === "object" && Array.isArray(item.frames)) {
        item.frames.forEach((frame) => flattened.push(frame));
      } else {
        flattened.push(item);
      }
    });
    const collapsed = normalizeFrames({ frames: flattened });
    if (collapsed.length > 0) return collapsed;
    return normalizeFrames(flattened);
  }
  if (typeof inlineFrames === "string") {
    return parseAnyText(inlineFrames);
  }
  return [];
}


function getQueryParam(name) {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  return params.get(name) ?? "";
}

export default function TherapistFail3D() {
  const demoParam = getQueryParam("demo");
  const demoFileParam = getQueryParam("demoFile");
  const demoUrl = demoFileParam || "/try-2690-20260203-170451 (1).jsonl";

  const [patientId, setPatientId] = useState(getQueryParam("patientId"));
  const sequenceIdParam = getQueryParam("sequenceId");
  const [sessions, setSessions] = useState([]);
  const [sequenceError, setSequenceError] = useState("");
  const [sequenceLoading, setSequenceLoading] = useState(false);

  const [sessionId, setSessionId] = useState(getQueryParam("sessionId"));
  const [failedTryIds, setFailedTryIds] = useState([]);
  const [failTryLabels, setFailTryLabels] = useState({});
  const [triesError, setTriesError] = useState("");
  const [triesLoading, setTriesLoading] = useState(false);

  const [selectedTryId, setSelectedTryId] = useState(getQueryParam("tryId"));
  const [frames, setFrames] = useState([]);
  const [framesLoading, setFramesLoading] = useState(false);
  const [framesError, setFramesError] = useState("");

  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  const framesRef = useRef([]);
  const cursorRef = useRef(0);
  const playingRef = useRef(false);
  const speedRef = useRef(1);
  const sessionIdRef = useRef(sessionId);
  const rafIdRef = useRef(null);
  const lastNowRef = useRef(null);
  const accMsRef = useRef(0);
  const periodMsRef = useRef(33.333);

  useEffect(() => {
    framesRef.current = frames;
  }, [frames]);

  useEffect(() => {
    cursorRef.current = cursor;
  }, [cursor]);

  useEffect(() => {
    playingRef.current = playing;
  }, [playing]);

  useEffect(() => {
    speedRef.current = speed;
  }, [speed]);
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const frame = useMemo(() => frames[cursor] ?? null, [frames, cursor]);

  const loadSequence = useCallback(async (nextPatientId) => {
    if (!nextPatientId) return;
    setSequenceLoading(true);
    setSequenceError("");
    try {
      console.log("[FAIL3D] loadSequence patientId", nextPatientId, "sequenceIdParam", sequenceIdParam);
      const res = await fetch(`${API_IOT_BASE_URL}/api/patients/${nextPatientId}/sequences`, {
        method: "GET",
      });
      if (!res.ok) throw new Error("시퀀스 정보를 불러오지 못했습니다.");
      const payload = await res.json();
      const sequenceList = Array.isArray(payload?.data)
        ? payload.data
        : Array.isArray(payload)
          ? payload
          : [];

      if (sequenceList.length == 0) {
        setSessions([]);
        setSessionId("");
        return;
      }

      let targetSequenceId = sequenceIdParam;
      if (!targetSequenceId) {
        const latest = sequenceList
          .slice()
          .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())[0];
        targetSequenceId = latest?.sequence_id ?? latest?.sequenceId ?? null;
      }

      if (!targetSequenceId) {
        setSessions([]);
        setSessionId("");
        return;
      }

      const detailRes = await fetch(
        `${API_IOT_BASE_URL}/api/patients/sequences/${targetSequenceId}`,
        { method: "GET" }
      );
      if (!detailRes.ok) throw new Error("시퀀스 정보를 불러오지 못했습니다.");
      const detailPayload = await detailRes.json();
      const detail = detailPayload?.data ?? detailPayload ?? {};
      const nextSessions = Array.isArray(detail?.sessions) ? detail.sessions : [];
      console.log("[FAIL3D] sequenceId", targetSequenceId, "sessions", nextSessions.map((s) => s.sessionId));
      setSessions(nextSessions);

      setSessionId((prev) => {
        const hasCurrent = nextSessions.some((s) => String(s.sessionId) === String(prev));
        if ((!prev || !hasCurrent) && nextSessions.length > 0) {
          return String(nextSessions[nextSessions.length - 1].sessionId);
        }
        return prev;
      });
    } catch (err) {
      setSequenceError(err?.message ?? "시퀀스 정보를 불러오지 못했습니다.");
      setSessions([]);
    } finally {
      setSequenceLoading(false);
    }
  }, [sequenceIdParam]);

  const loadFailedTries = useCallback(async (nextSessionId) => {
    if (!nextSessionId) return;
    setTriesLoading(true);
    setTriesError("");
    try {
      console.log("[FAIL3D] loadFailedTries sessionId", nextSessionId);
      const res = await fetch(`${API_IOT_BASE_URL}/sessions/${nextSessionId}/failed-tries`, {
        method: "GET",
      });
      if (!res.ok) throw new Error("실패 Try 목록을 불러오지 못했습니다.");
      const payload = await res.json();
      const list = Array.isArray(payload?.failedTryIds) ? payload.failedTryIds : [];
      console.log("[FAIL3D] failedTryIds", list);
      setFailedTryIds(list);
      setFailTryLabels({});
      if (list.length > 0) {
        setSelectedTryId((prev) => (prev ? prev : String(list[0])));
      }
    } catch (err) {
      setTriesError(err?.message ?? "실패 Try 목록을 불러오지 못했습니다.");
      setFailedTryIds([]);
      setFailTryLabels({});
    } finally {
      setTriesLoading(false);
    }
  }, []);

  const loadFailLogFrames = useCallback(async (nextTryId) => {
    if (!nextTryId) return;
    setFramesLoading(true);
    setFramesError("");
    try {
      console.log("[FAIL3D] loadFailLogFrames tryId", nextTryId);
      const res = await fetch(
        `${API_IOT_BASE_URL}/tries/${nextTryId}/fail-log-file`,
        { method: "GET" }
      );
      if (!res.ok) throw new Error("Fail log 데이터를 불러오지 못했습니다.");
      const contentType = res.headers.get("content-type") || "";
      let nextFrames = [];

      if (contentType.includes("application/json")) {
        const payload = await res.json();
        nextFrames = extractFramesFromPayload(payload);
      } else {
        const text = await res.text();
        if (text.trim().startsWith("<!doctype") || text.trim().startsWith("<html")) {
          throw new Error("Fail log 응답이 HTML입니다. API 경로/권한을 확인해주세요.");
        }
        nextFrames = parseAnyText(text);
      }

      setFrames(nextFrames);
      framesRef.current = nextFrames;
      setCursor(0);
      cursorRef.current = 0;
      periodMsRef.current = estimatePeriodMs(nextFrames);
      setPlaying(false);
      playingRef.current = false;
      lastNowRef.current = null;
      accMsRef.current = 0;
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    } catch (err) {
      setFramesError(err?.message ?? "Fail log 데이터를 불러오지 못했습니다.");
      setFrames([]);
    } finally {
      setFramesLoading(false);
    }
  }, []);

  const loadDemoFrames = useCallback(async () => {
    setFramesLoading(true);
    setFramesError("");
    try {
      const res = await fetch(demoUrl, { method: "GET" });
      if (!res.ok) throw new Error("데모 JSONL을 불러오지 못했습니다.");
      const text = await res.text();
      const nextFrames = parseAnyText(text);
      setFrames(nextFrames);
      framesRef.current = nextFrames;
      setCursor(0);
      cursorRef.current = 0;
      periodMsRef.current = estimatePeriodMs(nextFrames);
      setPlaying(false);
      playingRef.current = false;
      lastNowRef.current = null;
      accMsRef.current = 0;
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    } catch (err) {
      setFramesError(err?.message ?? "데모를 불러오지 못했습니다.");
      setFrames([]);
    } finally {
      setFramesLoading(false);
    }
  }, [demoUrl]);

  const handleFileLoad = async (file) => {
    if (!file) return;
    setFramesLoading(true);
    setFramesError("");
    try {
      const text = await file.text();
      const nextFrames = parseAnyText(text);
      if (!nextFrames.length) throw new Error("파일에 유효한 데이터가 없습니다.");
      setFrames(nextFrames);
      framesRef.current = nextFrames;
      setCursor(0);
      cursorRef.current = 0;
      periodMsRef.current = estimatePeriodMs(nextFrames);
      setPlaying(false);
      playingRef.current = false;
      lastNowRef.current = null;
      accMsRef.current = 0;
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    } catch (err) {
      setFramesError(err?.message ?? "파일을 불러오지 못했습니다.");
      setFrames([]);
    } finally {
      setFramesLoading(false);
    }
  };

  const fetchFailLabel = useCallback(async (tryId) => {
    if (!tryId) return null;
    try {
      const res = await fetch(`${API_IOT_BASE_URL}/tries/${tryId}/fail`, {
        method: "GET",
      });
      if (!res.ok) return null;
      const payload = await res.json();
      const first = payload?.fail_id || payload?.failId || "F_ELSE";
      return { id: first, label: FAIL_LABEL_MAP[first] ?? "기타 실패" };
    } catch {
      return null;
    }
  }, []);


  useEffect(() => {
    if (failedTryIds.length === 0) return;
    let cancelled = false;
    const run = async () => {
      const entries = await Promise.all(
        failedTryIds.map(async (id) => {
          const info = await fetchFailLabel(id);
          return [String(id), info];
        })
      );
      if (cancelled) return;
      const next = {};
      entries.forEach(([id, info]) => {
        if (info) next[id] = info;
      });
      setFailTryLabels(next);
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [failedTryIds, fetchFailLabel]);

  useEffect(() => {
    if (!patientId) return;
    loadSequence(patientId);
  }, [patientId, loadSequence]);

  useEffect(() => {
    if (!sessionId) return;
    setFailedTryIds([]);
    setSelectedTryId("");
    setFrames([]);
    setCursor(0);
    loadFailedTries(sessionId);
  }, [sessionId, loadFailedTries]);

  useEffect(() => {
    if (!selectedTryId) return;
    loadFailLogFrames(selectedTryId);
  }, [selectedTryId, loadFailLogFrames]);

  useEffect(() => {
    if (demoParam === "1" || demoParam === "true") {
      loadDemoFrames();
    }
  }, [demoParam, loadDemoFrames]);

  useEffect(() => {
    if (!playing || frames.length < 2) return;

    if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
    rafIdRef.current = null;
    lastNowRef.current = null;
    accMsRef.current = 0;

    const tick = (now) => {
      if (!playingRef.current) return;
      if (lastNowRef.current == null) lastNowRef.current = now;
      const dt = (now - lastNowRef.current) * speedRef.current;
      lastNowRef.current = now;

      accMsRef.current += dt;
      const stepMs = periodMsRef.current;

      if (accMsRef.current >= stepMs) {
        const steps = Math.floor(accMsRef.current / stepMs);
        accMsRef.current -= steps * stepMs;
        const fr = framesRef.current;
        const next = clamp(cursorRef.current + steps, 0, fr.length - 1);

        if (next !== cursorRef.current) {
          cursorRef.current = next;
          setCursor(next);
        }

        if (next >= fr.length - 1) {
          setPlaying(false);
          playingRef.current = false;
          lastNowRef.current = null;
          rafIdRef.current = null;
          return;
        }
      }

      rafIdRef.current = requestAnimationFrame(tick);
    };

    rafIdRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
      lastNowRef.current = null;
    };
  }, [playing, frames.length]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (
        document.activeElement instanceof HTMLInputElement ||
        document.activeElement instanceof HTMLSelectElement ||
        document.activeElement instanceof HTMLTextAreaElement
      ) {
        return;
      }
      switch (e.code) {
        case "Space":
          e.preventDefault();
          if (frames.length < 2) return;
          if (!playing) {
            lastNowRef.current = null;
            accMsRef.current = 0;
          }
          setPlaying((p) => !p);
          break;
        case "ArrowLeft":
          e.preventDefault();
          setPlaying(false);
          setCursor((c) => Math.max(0, c - 1));
          break;
        case "ArrowRight":
          e.preventDefault();
          setPlaying(false);
          setCursor((c) => Math.min(framesRef.current.length - 1, c + 1));
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [frames.length, playing]);

  const handleCursorChange = (i) => {
    const next = clamp(i, 0, frames.length - 1);
    setCursor(next);
    cursorRef.current = next;
    setPlaying(false);
    playingRef.current = false;
    lastNowRef.current = null;
    accMsRef.current = 0;
  };

  return (
    <div className="fail3d-shell">
      <div className="fail3d-header">
        <div className="fail3d-title">
          <span className="fail3d-badge">실패분석 3D</span>
          <span className="fail3d-subtitle">Fail Try Viewer</span>
        </div>
        <div className="fail3d-controls">
          <div className="fail3d-field">
            <span>환자 ID</span>
            <input
              className="fail3d-input"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              placeholder="patientId"
            />
          </div>
          <div className="fail3d-field">
            <span>세션</span>
            <select
              className="fail3d-select"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              disabled={sequenceLoading || sessions.length === 0}
            >
              {sessions.length === 0 && <option value="">세션 없음</option>}
              {sessions.map((s) => (
                <option key={s.sessionId} value={s.sessionId}>
                  {s.sessionId}
                </option>
              ))}
            </select>
          </div>
          <label className="fail3d-back" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            파일 선택
            <input
              type="file"
              accept=".jsonl,.ndjson,.json"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileLoad(file);
                e.target.value = "";
              }}
            />
          </label>
          <button
            className="fail3d-back"
            type="button"
            onClick={() => {
              window.location.href = "/therapist?view=lookup";
            }}
          >
            돌아가기
          </button>
        </div>
      </div>

      <div className="fail3d-content">
        <div className="fail3d-viewport">
          <div className="fail3d-panel">
            <div className="fail3d-time">
              {frame && frames.length > 0 && frames[0]?.ts?.video_ms != null
                ? `Time: ${(
                    (Number(frame.ts.video_ms) - Number(frames[0].ts.video_ms)) /
                    1000
                  ).toFixed(2)}s`
                : "Ready"}
            </div>
            <Pose3D frame={frame} />
          </div>
        </div>

        <div className="fail3d-analysis">
          {sequenceLoading && <div className="fail3d-empty">세션을 불러오는 중...</div>}
          {!sequenceLoading && sequenceError && <div className="fail3d-empty">{sequenceError}</div>}
          {triesLoading && <div className="fail3d-empty">실패 목록 불러오는 중...</div>}
          {!triesLoading && triesError && <div className="fail3d-empty">{triesError}</div>}

          {!framesLoading && framesError && <div className="fail3d-empty">{framesError}</div>}
          {framesLoading && <div className="fail3d-empty">Fail log 불러오는 중...</div>}

          {!framesLoading && !framesError && frames.length === 0 && (
            <div className="fail3d-empty">Fail log 데이터가 없습니다.</div>
          )}

          {frames.length > 0 && (
            <div className="fail3d-charts">
              <DetailCharts frames={frames} cursor={cursor} onCursorChange={handleCursorChange} />
            </div>
          )}
        </div>

        <div className="fail3d-side">
          <div className="fail3d-card">
            <div className="fail3d-card-title">실패 Try 목록</div>
            <div className="fail3d-try-list">
              {failedTryIds.length === 0 && <div className="fail3d-empty">실패 Try 없음</div>}
              {failedTryIds.map((id) => (
                <button
                  key={id}
                  className={`fail3d-try-item${String(selectedTryId) === String(id) ? " active" : ""}`}
                  type="button"
                  onClick={() => setSelectedTryId(String(id))}
                >
                  {`${failTryLabels[String(id)]?.label ?? "기타 실패"} #${id}`}
                </button>
              ))}
            </div>
          </div>
          <div className="fail3d-card">
            <div className="fail3d-card-title">Joint 요약</div>
            <div className="fail3d-card-body">
              <JointPanel frame={frame} />
            </div>
          </div>
        </div>
      </div>

      {frames.length > 0 && (
        <div className="fail3d-footer">
          <FooterTimeline frames={frames} cursor={cursor} onCursorChange={handleCursorChange} />
          <div className="fail3d-footer-controls">
            <div className="control-row">
              <button
                className="btn"
                type="button"
                onClick={() => {
                  setPlaying(false);
                  setCursor((c) => Math.max(0, c - 1));
                }}
              >
                이전
              </button>
              <button
                className={`btn ${playing ? "btn-primary" : ""}`}
                type="button"
                onClick={() => {
                  if (frames.length < 2) return;
                  if (!playing) {
                    lastNowRef.current = null;
                    accMsRef.current = 0;
                  }
                  setPlaying((p) => !p);
                }}
              >
                {playing ? "Pause" : "Play"}
              </button>
              <button
                className="btn"
                type="button"
                onClick={() => {
                  setPlaying(false);
                  setCursor((c) => Math.min(framesRef.current.length - 1, c + 1));
                }}
              >
                다음
              </button>
            </div>
            <div className="control-row">
              <span className="speed-label">Speed</span>
              <select
                className="select-input"
                value={speed}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setSpeed(v);
                  speedRef.current = v;
                  lastNowRef.current = null;
                  accMsRef.current = 0;
                }}
              >
                <option value={0.1}>0.1x</option>
                <option value={0.5}>0.5x</option>
                <option value={1}>1.0x</option>
                <option value={2}>2.0x</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

