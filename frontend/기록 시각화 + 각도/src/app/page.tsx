"use client";

import Link from "next/link";
import { useEffect, useState, useRef, useMemo } from "react";
import * as THREE from "three";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import { loadNdjson } from "@/lib/loadNdjson";
import DetailCharts, { FooterTimeline } from "@/components/Timeline";
import Pose3D from "@/components/Pose3D";

import type { Frame } from "@/types";

function estimatePeriodMs(frames: Frame[]) {
  if (frames.length < 2) return 33;
  const t0 = frames[0].ts.video_ms ?? 0;
  const tN = frames[frames.length - 1].ts.video_ms ?? 0;
  const span = tN - t0;
  const avg = span / (frames.length - 1);
  return avg > 0 ? avg : 33;
}

function clamp(v: number, mn: number, mx: number) {
  return Math.max(mn, Math.min(mx, v));
}

export default function Home() {
  const [frames, setFrames] = useState<Frame[]>([]);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [loading, setLoading] = useState(false);

  // ---------- refs (stale closure 방지) ----------
  const framesRef = useRef<Frame[]>([]);
  const cursorRef = useRef(0);
  const playingRef = useRef(false);
  const speedRef = useRef(1);

  const rafIdRef = useRef<number | null>(null);
  const lastNowRef = useRef<number | null>(null);
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

  const frame = useMemo(() => frames[cursor] ?? null, [frames, cursor]);

  // ---------- autoplay loop ----------
  useEffect(() => {
    if (!playing || frames.length < 2) return;

    if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
    rafIdRef.current = null;
    lastNowRef.current = null;
    accMsRef.current = 0;

    const tick = (now: number) => {
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

  // ---------- file load ----------
  const onLoadFile = async (f: File) => {
    setLoading(true);
    try {
      const loaded = await loadNdjson(f);

      setFrames(loaded);
      framesRef.current = loaded;

      setCursor(0);
      cursorRef.current = 0;

      periodMsRef.current = estimatePeriodMs(loaded);

      setPlaying(false);
      playingRef.current = false;

      lastNowRef.current = null;
      accMsRef.current = 0;

      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    } catch (e) {
      console.error("Failed to load file:", e);
      alert("파일 로드 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const togglePlay = () => {
    if (frames.length < 2) return;
    if (!playing) {
      // 시작할 때 시간 기준 리셋 (점프 방지)
      lastNowRef.current = null;
      accMsRef.current = 0;
    }
    setPlaying((p) => !p);
  };

  // ---------- keyboard events ----------
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 입력 요소에 포커스된 경우 무시
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
          togglePlay();
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
  }, [frames.length]);

  // Cursor change handler
  const handleCursorChange = (i: number) => {
    const next = clamp(i, 0, frames.length - 1);
    setCursor(next);
    cursorRef.current = next;

    setPlaying(false);
    playingRef.current = false;
    lastNowRef.current = null;
    accMsRef.current = 0;
  };

  return (
    <div className="dashboard-container" style={{ flexDirection: "column" }}>
      {/* 1. Header */}
      <div className="dashboard-header">
        <div className="brand-title">
          <span style={{ color: "#3b82f6" }}>⚡</span> Pose Clinic Analytics
        </div>

        {/* Controls Removed from Header */}
        <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center" }}>
          <div className="badge">
            {frames.length > 0 ? `${frames.length} frames` : "No Data"}
          </div>
          <input
            type="file"
            accept=".ndjson,.jsonl"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onLoadFile(f);
            }}
            style={{ fontSize: "0.85rem", color: "#94a3b8" }}
          />
        </div>
      </div>

      {/* 2. Main Content (Left: 3D, Center: Charts, Right: Data) */}
      <div className="dashboard-content" style={{ flexDirection: "row", paddingBottom: 140 }}>
        {/* paddingBottom matches footer height */}

        {/* Left: 3D Pose (60%) */}
        <div className="viewport-section" style={{ flex: "0 0 60%", borderRight: "1px solid var(--panel-border)" }}>
          <div className="panel-plain">
            <div style={{ position: "absolute", top: 12, right: 12, zIndex: 10, background: "rgba(15,23,42,0.8)", padding: "4px 8px", borderRadius: 4, fontSize: 12, color: "#fff" }}>
              {frame ? `Time: ${((frame.ts.video_ms - frames[0].ts.video_ms) / 1000).toFixed(2)}s` : "Ready"}
            </div>
            <Pose3D frame={frame} />
          </div>
        </div>

        {/* Center: Charts (Flexible) */}
        <div className="analysis-section" style={{ flex: 1, display: "flex", flexDirection: "column", border: "none", background: "transparent" }}>
          {loading ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
              Processing...
            </div>
          ) : frames.length === 0 ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
              Waiting for File...
            </div>
          ) : (
            <div style={{ flex: 1, padding: 12 }}>
              <DetailCharts frames={frames} cursor={cursor} onCursorChange={handleCursorChange} />
            </div>
          )}
        </div>
      </div>

      {/* 4. Bottom Dock (Timeline + Controls) */}
      {frames.length > 0 && (
        <div className="bottom-dock">
          {/* Left: Timeline */}
          <FooterTimeline frames={frames} cursor={cursor} onCursorChange={handleCursorChange} />

          {/* Right: Controls */}
          <div className="controls-dock">
            <div className="control-row">
              <button
                className="btn"
                onClick={() => { setPlaying(false); setCursor(c => c - 1); }}
                title="-1 Frame"
              >◀</button>
              <button
                onClick={togglePlay}
                className={`btn ${playing ? "btn-primary" : ""}`}
                style={{ width: 100, justifyContent: "center" }}
              >
                {playing ? "❚❚ Pause" : "▶ Play"}
              </button>
              <button
                className="btn"
                onClick={() => { setPlaying(false); setCursor(c => c + 1); }}
                title="+1 Frame"
              >▶</button>
            </div>

            <div className="control-row">
              <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Speed</span>
              <select
                value={speed}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setSpeed(v);
                  speedRef.current = v;
                  lastNowRef.current = null;
                  accMsRef.current = 0;
                }}
                className="select-input"
                style={{ padding: "2px 8px", fontSize: "0.8rem" }}
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
