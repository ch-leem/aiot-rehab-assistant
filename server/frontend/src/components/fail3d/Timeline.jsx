import { useMemo } from "react";
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

function findNearestIndexByTime(data, t) {
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

function useTimelineData(frames) {
  const t0 = frames[0]?.ts?.video_ms ?? 0;
  return useMemo(
    () =>
      frames.map((f, i) => {
        const rawT = (Number(f.ts?.video_ms ?? 0) - t0) / 1000;
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

export default function DetailCharts({ frames, cursor, onCursorChange }) {
  const data = useTimelineData(frames);
  const curT = data[cursor]?.t ?? 0;
  const minT = data[0]?.t ?? 0;
  const maxT = data[data.length - 1]?.t ?? 0;

  const windowSec = 8;
  const winStart = Math.max(minT, curT - windowSec);
  const winEnd = Math.max(minT + windowSec, curT);

  const slidingData = useMemo(() => {
    const sT = Math.max(minT, winStart - 2);
    const eT = Math.min(maxT, winEnd + 2);
    const sIdx = findNearestIndexByTime(data, sT);
    const eIdx = findNearestIndexByTime(data, eT);
    return data.slice(sIdx, eIdx + 1);
  }, [data, winStart, winEnd, minT, maxT]);

  const noAnim = { isAnimationActive: false, animationDuration: 0 };

  const { strengthDomain, powerDomain } = useMemo(() => {
    let sMin = Infinity;
    let sMax = -Infinity;
    let pMin = Infinity;
    let pMax = -Infinity;
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
    if (sMin === Infinity) {
      sMin = 0;
      sMax = 100;
    }
    if (pMin === Infinity) {
      pMin = 0;
      pMax = 100;
    }
    const sPad = (sMax - sMin) * 0.1 || 1;
    const pPad = (pMax - pMin) * 0.1 || 1;
    return {
      strengthDomain: [sMin, sMax + sPad],
      powerDomain: [pMin, pMax + pPad],
    };
  }, [data]);

  const curStrength = data[cursor]?.strength ?? 0;
  const curPower = data[cursor]?.power ?? 0;

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ flex: 1, minHeight: 0, position: "relative", background: "#f8faff", borderRadius: 8, border: "1px solid #dbe3f3" }}>
        <div style={{ position: "absolute", top: 8, left: 12, zIndex: 10 }}>
          <div style={{ fontSize: 13, color: "#64748b", fontWeight: 500 }}>Hand Speed</div>
          <div style={{ fontSize: 24, color: "#22c55e", fontWeight: 700, marginTop: -2 }}>
            {curStrength.toFixed(1)} <span style={{ fontSize: 14, opacity: 0.7 }}>deg/s</span>
          </div>
        </div>

        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={slidingData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            onClick={(e) => {
              const i = e?.activeTooltipIndex;
              if (typeof i === "number") {
                const orig = slidingData[i]?.i;
                if (typeof orig === "number") onCursorChange(orig);
              }
            }}
          >
            <XAxis dataKey="t" type="number" domain={[winStart, winEnd]} allowDataOverflow hide />
            <YAxis domain={strengthDomain} hide />
            <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #dbe3f3", color: "#1e293b" }} labelFormatter={() => ""} />
            <ReferenceLine x={curT} stroke="#eab308" strokeWidth={2} />
            <Line type="monotone" dataKey="strength" stroke="#22c55e" strokeWidth={3} dot={false} {...noAnim} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ flex: 1, minHeight: 0, position: "relative", background: "#f8faff", borderRadius: 8, border: "1px solid #dbe3f3" }}>
        <div style={{ position: "absolute", top: 8, left: 12, zIndex: 10 }}>
          <div style={{ fontSize: 13, color: "#64748b", fontWeight: 500 }}>Weight Load</div>
          <div style={{ fontSize: 24, color: "#3b82f6", fontWeight: 700, marginTop: -2 }}>
            {curPower.toFixed(1)} <span style={{ fontSize: 14, opacity: 0.7 }}>kg</span>
          </div>
        </div>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={slidingData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            onClick={(e) => {
              const i = e?.activeTooltipIndex;
              if (typeof i === "number") {
                const orig = slidingData[i]?.i;
                if (typeof orig === "number") onCursorChange(orig);
              }
            }}
          >
            <XAxis dataKey="t" type="number" domain={[winStart, winEnd]} allowDataOverflow stroke="#94a3b8" tickFormatter={(v) => v.toFixed(1)} />
            <YAxis domain={powerDomain} hide />
            <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #dbe3f3", color: "#1e293b" }} labelFormatter={(v) => `${Number(v).toFixed(2)}s`} />
            <ReferenceLine x={curT} stroke="#eab308" strokeWidth={2} />
            <Line type="monotone" dataKey="power" stroke="#3b82f6" strokeWidth={3} dot={false} {...noAnim} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function FooterTimeline({ frames, cursor, onCursorChange }) {
  const data = useTimelineData(frames);
  const curT = data[cursor]?.t ?? 0;

  const onSequenceClick = (e) => {
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
              contentStyle={{ background: "#ffffff", border: "1px solid #dbe3f3", color: "#1e293b" }}
              labelFormatter={(v) => `t=${Number(v).toFixed(2)}s`}
            />
            <ReferenceLine x={curT} stroke="#eab308" strokeWidth={2} />
            <Line type="monotone" dataKey="strength" stroke="#22c55e" strokeWidth={1} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="power" stroke="#3b82f6" strokeWidth={1} dot={false} isAnimationActive={false} />
            <Brush dataKey="t" height={30} stroke="#94a3b8" travellerWidth={10} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
