// components/Timeline.tsx
"use client";

import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Brush,
} from "recharts";
import type { Frame } from "@/types";

function findNearestIndexByTime(data: { t: number }[], t: number) {
  let lo = 0;
  let hi = data.length - 1;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (data[mid].t < t) lo = mid + 1;
    else hi = mid;
  }
  if (lo <= 0) return 0;
  if (lo >= data.length) return data.length - 1;
  return Math.abs(data[lo].t - t) < Math.abs(data[lo - 1].t - t) ? lo : lo - 1;
}

// Data Preparation Hook
function useTimelineData(frames: Frame[]) {
  const t0 = frames[0]?.ts.video_ms ?? 0;
  return useMemo(
    () =>
      frames.map((f, i) => {
        const rawT = (f.ts.video_ms - t0) / 1000;
        return {
          i,
          t: Number.isFinite(rawT) ? rawT : 0,
          strength: f.sensor?.strength ?? 0,
          power: f.sensor?.power ?? 0,
        };
      }),
    [frames, t0]
  );
}

// 1. Detail Charts (Upper)
export default function DetailCharts({
  frames,
  cursor,
  onCursorChange,
}: {
  frames: Frame[];
  cursor: number;
  onCursorChange: (idx: number) => void;
}) {
  const data = useTimelineData(frames);
  const curT = data[cursor]?.t ?? 0;
  const minT = data[0]?.t ?? 0;
  const maxT = data[data.length - 1]?.t ?? 0;

  // 8-second sliding window
  const windowSec = 8;
  const winStart = Math.max(minT, curT - windowSec);
  const winEnd = Math.max(minT + windowSec, curT); // Follow cursor

  const slidingData = useMemo(() => {
    // Buffer for smooth rendering
    const sT = Math.max(minT, winStart - 2);
    const eT = Math.min(maxT, winEnd + 2);
    const sIdx = findNearestIndexByTime(data, sT);
    const eIdx = findNearestIndexByTime(data, eT);
    return data.slice(sIdx, eIdx + 1);
  }, [data, winStart, winEnd, minT, maxT]);

  const noAnim = { isAnimationActive: false, animationDuration: 0 };

  const { strengthDomain, powerDomain } = useMemo(() => {
    let sMin = Infinity, sMax = -Infinity;
    let pMin = Infinity, pMax = -Infinity;
    for (const d of data) {
      if (Number.isFinite(d.strength)) {
        sMin = Math.min(sMin, d.strength);
        sMax = Math.max(sMax, d.strength);
      }
      if (Number.isFinite(d.power)) {
        pMin = Math.min(pMin, d.power);
        pMax = Math.max(pMax, d.power);
      }
    }
    // Default fallback
    if (sMin === Infinity) { sMin = 0; sMax = 100; }
    if (pMin === Infinity) { pMin = 0; pMax = 100; }

    // Add 10% padding
    const sPad = (sMax - sMin) * 0.1 || 1;
    const pPad = (pMax - pMin) * 0.1 || 1;

    return {
      strengthDomain: [sMin, sMax + sPad] as [number, number],
      powerDomain: [pMin, pMax + pPad] as [number, number],
    };
  }, [data]);

  const curStrength = data[cursor]?.strength ?? 0;
  const curPower = data[cursor]?.power ?? 0;

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Strength */}
      <div style={{ flex: 1, minHeight: 0, position: "relative", background: "rgba(15, 23, 42, 0.3)", borderRadius: 8, border: "1px solid rgba(148,163,184,0.1)" }}>
        {/* Title & Value Overlay */}
        <div style={{ position: "absolute", top: 8, left: 12, zIndex: 10 }}>
          <div style={{ fontSize: 13, color: "#94a3b8", fontWeight: 500 }}>Hand Speed</div>
          <div style={{ fontSize: 24, color: "#22c55e", fontWeight: 700, marginTop: -2 }}>
            {curStrength.toFixed(1)} <span style={{ fontSize: 14, opacity: 0.7 }}>deg/s</span>
          </div>
        </div>

        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={slidingData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            onClick={(e: any) => {
              const i = e?.activeTooltipIndex;
              if (typeof i === "number") {
                const orig = slidingData[i]?.i;
                if (typeof orig === "number") onCursorChange(orig);
              }
            }}
          >
            <XAxis dataKey="t" type="number" domain={[winStart, winEnd]} allowDataOverflow hide />
            <YAxis domain={strengthDomain} hide />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", color: "#fff" }} labelFormatter={() => ''} />
            <ReferenceLine x={curT} stroke="#eab308" strokeWidth={2} />
            <Line type="monotone" dataKey="strength" stroke="#22c55e" strokeWidth={3} dot={false} {...noAnim} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Power */}
      <div style={{ flex: 1, minHeight: 0, position: "relative", background: "rgba(15, 23, 42, 0.3)", borderRadius: 8, border: "1px solid rgba(148,163,184,0.1)" }}>
        {/* Title & Value Overlay */}
        <div style={{ position: "absolute", top: 8, left: 12, zIndex: 10 }}>
          <div style={{ fontSize: 13, color: "#94a3b8", fontWeight: 500 }}>Weight Load</div>
          <div style={{ fontSize: 24, color: "#3b82f6", fontWeight: 700, marginTop: -2 }}>
            {curPower.toFixed(1)} <span style={{ fontSize: 14, opacity: 0.7 }}>kg</span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={slidingData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            onClick={(e: any) => {
              const i = e?.activeTooltipIndex;
              if (typeof i === "number") {
                const orig = slidingData[i]?.i;
                if (typeof orig === "number") onCursorChange(orig);
              }
            }}
          >
            <XAxis dataKey="t" type="number" domain={[winStart, winEnd]} allowDataOverflow stroke="#64748b" tickFormatter={(v) => v.toFixed(1)} />
            <YAxis domain={powerDomain} hide />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", color: "#fff" }} labelFormatter={(v) => `${Number(v).toFixed(2)}s`} />
            <ReferenceLine x={curT} stroke="#eab308" strokeWidth={2} />
            <Line type="monotone" dataKey="power" stroke="#3b82f6" strokeWidth={3} dot={false} {...noAnim} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// 2. Footer Timeline (Bottom)
export function FooterTimeline({
  frames,
  cursor,
  onCursorChange,
}: {
  frames: Frame[];
  cursor: number;
  onCursorChange: (idx: number) => void;
}) {
  const data = useTimelineData(frames);
  const curT = data[cursor]?.t ?? 0;

  const onSequenceClick = (e: any) => {
    const t = e?.activeLabel;
    if (typeof t === "number") {
      const idx = findNearestIndexByTime(data, t);
      onCursorChange(idx);
    }
  };

  return (
    <div className="timeline-footer">
      <div className="timeline-content-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} onClick={onSequenceClick}>
            <XAxis dataKey="t" type="number" hide domain={["dataMin", "dataMax"]} />
            <YAxis hide />
            <Tooltip
              contentStyle={{ background: "#020617", border: "1px solid #334155", color: "#e5e7eb" }}
              labelFormatter={(v) => `t=${Number(v).toFixed(2)}s`}
            />
            <ReferenceLine x={curT} stroke="#eab308" strokeWidth={2} />
            {/* Show compressed view */}
            <Line type="monotone" dataKey="strength" stroke="#22c55e" strokeWidth={1} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="power" stroke="#3b82f6" strokeWidth={1} dot={false} isAnimationActive={false} />
            <Brush dataKey="t" height={30} stroke="#64748b" travellerWidth={10} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
