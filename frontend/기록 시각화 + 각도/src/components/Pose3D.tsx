// components/Pose3D.tsx
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree, useFrame } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import type { Frame, Joint } from "@/types";
import * as THREE from "three";

// --- Constants & Types ---
const USE_TUBES = true;
const JOINT_RADIUS = 0.03;
const LINE_WIDTH = 2;
const TUBE_RADIUS = 0.015;

type Side = "left" | "right" | "mid";
type View = "front" | "side" | "top";

const EDGES: Array<[string, string, Side]> = [
  ["left_shoulder", "left_elbow", "left"],
  ["left_elbow", "left_wrist", "left"],
  ["right_shoulder", "right_elbow", "right"],
  ["right_elbow", "right_wrist", "right"],
  ["left_hip", "left_knee", "left"],
  ["left_knee", "left_ankle", "left"],
  ["right_hip", "right_knee", "right"],
  ["right_knee", "right_ankle", "right"],
  ["left_shoulder", "left_hip", "left"],
  ["right_shoulder", "right_hip", "right"],
];

const CROSS_EDGES: Array<[string, string]> = [
  ["left_shoulder", "right_shoulder"],
  ["left_hip", "right_hip"],
];

// Target joints for HUD
const HUD_TARGETS = [
  { key: "shoulder", label: "Shoulder", angleKey: "shoulder_flexion", topPct: 20 },
  { key: "elbow", label: "Elbow", angleKey: "elbow_extension", topPct: 35 },
  { key: "hip", label: "Hip", angleKey: "hip_flexion", topPct: 50 },
  { key: "knee", label: "Knee", angleKey: "knee_flexion", topPct: 65 },
  { key: "ankle", label: "Ankle", angleKey: "ankle_plantarflexion", topPct: 80 },
] as const;


// --- Helper Functions ---
function toVec(j: Joint) {
  return new THREE.Vector3(j.x, -j.y, -j.z);
}

function getJoint(frame: Frame, side: Side, name: string): Joint | null {
  return frame.position?.[side]?.[name] ?? null;
}

function computeBounds(frame: Frame) {
  const pts: THREE.Vector3[] = [];
  (["left", "right", "mid"] as const).forEach((side) => {
    const g = frame.position?.[side] ?? {};
    for (const j of Object.values(g)) pts.push(toVec(j as Joint));
  });

  if (!pts.length) return { center: new THREE.Vector3(), radius: 1 };

  const box = new THREE.Box3().setFromPoints(pts);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const radius = Math.max(size.x, size.y, size.z) * 0.6;

  return { center, radius: Math.max(radius, 0.3) };
}

// --- 3D Components ---

function BoneTube({ a, b, color, opacity }: { a: THREE.Vector3; b: THREE.Vector3; color: string; opacity: number }) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const len = dir.length();
  if (len < 1e-6) return null;

  const mid = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5);
  const quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());

  return (
    <mesh position={mid} quaternion={quat}>
      <cylinderGeometry args={[TUBE_RADIUS, TUBE_RADIUS, len, 8]} />
      <meshStandardMaterial color={color} transparent opacity={opacity} roughness={0.4} />
    </mesh>
  );
}

function FootTriangle({ heel, ankle, toe, color }: { heel: THREE.Vector3; ankle: THREE.Vector3; toe: THREE.Vector3; color: string }) {
  const geom = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const verts = new Float32Array([heel.x, heel.y, heel.z, ankle.x, ankle.y, ankle.z, toe.x, toe.y, toe.z]);
    g.setAttribute("position", new THREE.BufferAttribute(verts, 3));
    g.setIndex([0, 1, 2]);
    g.computeVertexNormals();
    return g;
  }, [heel, ankle, toe]);

  return (
    <mesh geometry={geom}>
      <meshBasicMaterial color={color} transparent opacity={0.25} side={THREE.DoubleSide} />
    </mesh>
  );
}

// --- Connector Component (Lives inside Canvas) ---
function HudConnector({ frame, linesRef }: { frame: Frame, linesRef: React.MutableRefObject<Map<string, SVGLineElement>> }) {
  const { camera, size } = useThree();

  useFrame(() => {
    if (!frame) return;

    (["left", "right"] as const).forEach(side => {
      HUD_TARGETS.forEach(target => {
        const lineId = `${side}-${target.key}-line`;
        const lineEl = linesRef.current.get(lineId);
        if (!lineEl) return;

        // 1. Get 3D Joint Position
        const fullJointName = `${side}_${target.key}`;
        const jointData = getJoint(frame, side, fullJointName);

        if (jointData) {
          const vec = toVec(jointData);

          // 2. Project to 2D Screen Coordinates
          vec.project(camera);

          // Check if it's behind the camera
          if (vec.z > 1) {
            lineEl.style.opacity = "0";
            return;
          }

          const x = (vec.x * .5 + .5) * size.width;
          const y = (-(vec.y * .5) + .5) * size.height;

          // 3. Calculate Fixed Label Anchor Position
          // Swap Sides: Left Body (Green) -> Right Screen Edge | Right Body (Blue) -> Left Screen Edge

          const labelX = side === "left" ? size.width - 60 : 60;
          const labelY = size.height * (target.topPct / 100);

          // 4. Update SVG Line
          lineEl.setAttribute("x1", x.toString());
          lineEl.setAttribute("y1", y.toString());
          lineEl.setAttribute("x2", labelX.toString());
          lineEl.setAttribute("y2", labelY.toString());
          lineEl.style.opacity = "1";
        } else {
          lineEl.style.opacity = "0";
        }
      });
    });
  });

  return null; // Logic only
}

function PoseScene({ frame, view, requestFitNonce }: { frame: Frame; view: View; requestFitNonce: number }) {
  const { camera } = useThree();
  const controlsRef = useRef<any>(null);
  const bounds = useMemo(() => computeBounds(frame), [frame]);

  useEffect(() => {
    const { center, radius } = bounds;
    const fov = (camera as THREE.PerspectiveCamera).fov;
    const dist = (radius / Math.tan((fov * Math.PI) / 360)) * 1.3;

    const pos = view === "front" ? new THREE.Vector3(center.x, center.y, center.z + dist) :
      view === "side" ? new THREE.Vector3(center.x + dist, center.y, center.z) :
        new THREE.Vector3(center.x, center.y + dist, center.z);

    camera.position.copy(pos);
    camera.updateProjectionMatrix();
    controlsRef.current?.target.copy(center);
    controlsRef.current?.update();
  }, [requestFitNonce]); // Only update when explicitly requested

  return (
    <>
      <ambientLight intensity={0.7} />
      <directionalLight position={[2, 3, 2]} intensity={1.2} />

      {/* Joints */}
      {(["left", "right", "mid"] as const).flatMap((side) =>
        Object.entries(frame.position?.[side] ?? {}).map(([name, j]) => (
          <mesh key={`${side}:${name}`} position={toVec(j as Joint)}>
            <sphereGeometry args={[JOINT_RADIUS]} />
            <meshStandardMaterial color={side === "left" ? "#22c55e" : side === "right" ? "#3b82f6" : "#eab308"} transparent opacity={0.9} />
          </mesh>
        ))
      )}

      {/* Bones */}
      {EDGES.map(([a, b, side], i) => {
        const ja = getJoint(frame, side, a);
        const jb = getJoint(frame, side, b);
        if (!ja || !jb) return null;
        return USE_TUBES ?
          <BoneTube key={i} a={toVec(ja)} b={toVec(jb)} color="#f8fafc" opacity={0.85} /> :
          <Line key={i} points={[toVec(ja).toArray() as any, toVec(jb).toArray() as any]} color="#f8fafc" lineWidth={LINE_WIDTH} />;
      })}

      {/* Cross edges */}
      {CROSS_EDGES.map(([a, b], i) => {
        const ja = getJoint(frame, "left", a);
        const jb = getJoint(frame, "right", b);
        if (!ja || !jb) return null;
        return <Line key={`cross-${i}`} points={[toVec(ja).toArray() as any, toVec(jb).toArray() as any]} color="#e5e7eb" lineWidth={1} opacity={0.6} />;
      })}

      {/* Foot Triangles */}
      {(["left", "right"] as const).map((side) => {
        const heelJ = getJoint(frame, side, `${side}_heel`);
        const ankleJ = getJoint(frame, side, `${side}_ankle`);
        const toeJ = getJoint(frame, side, `${side}_toe`);
        if (!heelJ || !ankleJ || !toeJ) return null;
        const heel = toVec(heelJ);
        const ankle = toVec(ankleJ);
        const toe = toVec(toeJ);
        const color = side === "left" ? "#22c55e" : "#3b82f6";

        return (
          <React.Fragment key={`foot-${side}`}>
            <FootTriangle heel={heel} ankle={ankle} toe={toe} color={color} />
            {USE_TUBES ? (
              <>
                <BoneTube a={heel} b={ankle} color={color} opacity={0.95} />
                <BoneTube a={ankle} b={toe} color={color} opacity={0.95} />
                <BoneTube a={toe} b={heel} color={color} opacity={0.95} />
              </>
            ) : (
              <>{[[heel, ankle], [ankle, toe], [toe, heel]].map((pts, k) => <Line key={k} points={[pts[0].toArray() as any, pts[1].toArray() as any]} color={color} lineWidth={LINE_WIDTH} />)}</>
            )}
          </React.Fragment>
        );
      })}

      <OrbitControls ref={controlsRef} makeDefault enablePan={false} />
    </>
  );
}

// --- Main Export with Overlay Wrapper ---
export default function Pose3D({ frame }: { frame: Frame | null }) {
  const [view, setView] = useState<View>("front");
  const [fitNonce, setFitNonce] = useState(0);

  // Store refs to SVG Line elements
  const linesRef = useRef<Map<string, SVGLineElement>>(new Map());

  // ✅ Fix: Only trigger fit on view change (or first load), NOT every frame
  useEffect(() => {
    setFitNonce((n) => n + 1);
  }, [view]);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative", overflow: "hidden" }}>
      {/* 1. 3D Layer */}
      <div style={{ width: "100%", height: "100%", zIndex: 1 }}>
        {frame && (
          <Canvas camera={{ position: [0, 0.3, 2.2], fov: 50 }}>
            <PoseScene frame={frame} view={view} requestFitNonce={fitNonce} />
            {/* The Connector updates the lines in the Overlay */}
            <HudConnector frame={frame} linesRef={linesRef} />
          </Canvas>
        )}
      </div>

      {/* 2. HUD Overlay Layer (Z-Index > Canvas) */}
      {frame && (
        <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", zIndex: 10, pointerEvents: "none" }}>

          {/* SVG Layer for Connector Lines */}
          <svg width="100%" height="100%" style={{ position: "absolute", top: 0, left: 0, overflow: "visible" }}>
            {(["left", "right"] as const).flatMap(side =>
              HUD_TARGETS.map(target => (
                <line
                  key={`${side}-${target.key}-line`}
                  ref={(el) => { if (el) linesRef.current.set(`${side}-${target.key}-line`, el); }}
                  stroke={side === "left" ? "#22c55e" : "#3b82f6"} // Green / Blue
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                  opacity="0"
                // Initial coordinates are handled by HudConnector
                />
              ))
            )}
          </svg>

          {/* Static HTML Labels */}
          {(["left", "right"] as const).map(side => (
            <React.Fragment key={side}>
              {HUD_TARGETS.map(target => {
                const val = frame.deg?.[side]?.[target.angleKey];
                return (
                  <div
                    key={target.key}
                    style={{
                      position: "absolute",
                      top: `${target.topPct}%`,
                      // Swap Sides: Left Body -> Right Screen | Right Body -> Left Screen
                      [side === "left" ? "right" : "left"]: "20px",
                      width: "80px",
                      transform: "translateY(-50%)",
                      background: "rgba(15, 23, 42, 0.85)",
                      border: `1px solid ${side === "left" ? "#22c55e" : "#3b82f6"}`,
                      borderRadius: "6px",
                      padding: "6px 10px",
                      color: "#fff",
                      textAlign: side === "left" ? "right" : "left", // Align text towards edge? Or keep standard? Let's align to edge.
                      pointerEvents: "auto",
                      backdropFilter: "blur(4px)"
                    }}
                  >
                    <div style={{ fontSize: "18px", fontWeight: "bold", lineHeight: 1 }}>
                      {typeof val === 'number' ? val.toFixed(0) : "-"}°
                    </div>
                    <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: 2, textTransform: "uppercase" }}>
                      {target.label}
                    </div>
                  </div>
                )
              })}
            </React.Fragment>
          ))}

          {/* View Controls (Moved to Overlay) */}
          <div style={{ position: "absolute", top: 12, left: 12, display: "flex", gap: 8, pointerEvents: "auto" }}>
            {(["front", "side", "top"] as const).map((v) => (
              <button key={v} onClick={() => setView(v)} style={btn(view === v)}>
                {v}
              </button>
            ))}
          </div>

          {/* Time Indicator */}
          {/* Can be kept here or in page.tsx. Let's keep it clean here if possible, but page.tsx has it. */}
        </div>
      )}
    </div>
  );
}

function btn(active: boolean): React.CSSProperties {
  return {
    padding: "6px 10px",
    borderRadius: 10,
    background: active ? "rgba(226,232,240,0.2)" : "rgba(2,6,23,0.35)",
    color: "#e5e7eb",
    border: "1px solid rgba(148,163,184,0.35)",
    cursor: "pointer",
    textTransform: "capitalize",
    fontSize: "12px",
    fontWeight: 500
  };
}
