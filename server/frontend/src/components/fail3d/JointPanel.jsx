import { useMemo } from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const targets = [
  { label: "Shoulder", key: "shoulder_flexion" },
  { label: "Elbow", key: "elbow_extension" },
  { label: "Hip", key: "hip_flexion" },
  { label: "Knee", key: "knee_flexion" },
  { label: "Ankle", key: "ankle_plantarflexion" },
];

function formatVal(v) {
  if (typeof v !== "number") return "-";
  return v.toFixed(1);
}

export default function JointPanel({ frame }) {
  const chartData = useMemo(() => {
    if (!frame) return [];
    return targets.map((t) => ({
      subject: t.label,
      left: frame.deg?.left?.[t.key] ?? 0,
      right: frame.deg?.right?.[t.key] ?? 0,
      fullMark: 180,
    }));
  }, [frame]);

  const symmetryScore = useMemo(() => {
    if (!frame) return "0";
    let totalDiff = 0;
    targets.forEach((t) => {
      const l = frame.deg?.left?.[t.key] ?? 0;
      const r = frame.deg?.right?.[t.key] ?? 0;
      totalDiff += Math.abs(l - r);
    });
    const avgDiff = totalDiff / targets.length;
    return Math.max(0, 100 - avgDiff).toFixed(0);
  }, [frame]);

  if (!frame) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
        No Data
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <div style={{ flex: 1, minHeight: 0, position: "relative" }}>
        <div style={{ position: "absolute", top: 10, left: 10, zIndex: 10 }}>
          <div style={{ fontSize: 12, color: "#64748b" }}>Symmetry</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: "#1e293b" }}>{symmetryScore}%</div>
        </div>

        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={chartData}>
            <PolarGrid stroke="#dbe3f3" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: "#64748b", fontSize: 11 }} />
            <PolarRadiusAxis angle={30} domain={[0, 180]} tick={false} axisLine={false} />
            <Radar name="Left" dataKey="left" stroke="#22c55e" strokeWidth={2} fill="#22c55e" fillOpacity={0.3} />
            <Radar name="Right" dataKey="right" stroke="#3b82f6" strokeWidth={2} fill="#3b82f6" fillOpacity={0.3} />
            <Tooltip
              contentStyle={{ background: "#ffffff", border: "1px solid #dbe3f3", color: "#1e293b", fontSize: 12 }}
              listStyle={{ padding: 0 }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ padding: "0 12px 12px 12px", background: "transparent" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 8, paddingBottom: 8, borderBottom: "1px solid #dbe3f3", marginBottom: 8 }}>
          <div style={{ textAlign: "right", fontSize: 11, fontWeight: 600, color: "#22c55e" }}>LEFT</div>
          <div style={{ textAlign: "center", fontSize: 11, fontWeight: 600, color: "#94a3b8" }}>JOINT</div>
          <div style={{ textAlign: "left", fontSize: 11, fontWeight: 600, color: "#3b82f6" }}>RIGHT</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {targets.map((t) => {
            const lVal = frame.deg?.left?.[t.key];
            const rVal = frame.deg?.right?.[t.key];
            return (
              <div key={t.key} style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 8, alignItems: "center" }}>
                <div style={{ textAlign: "right", fontFamily: "monospace", fontSize: 13, color: "#1e293b" }}>
                  {formatVal(lVal)}
                </div>
                <div style={{ textAlign: "center", fontSize: 12, color: "#64748b", width: 60 }}>
                  {t.label}
                </div>
                <div style={{ textAlign: "left", fontFamily: "monospace", fontSize: 13, color: "#1e293b" }}>
                  {formatVal(rVal)}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
