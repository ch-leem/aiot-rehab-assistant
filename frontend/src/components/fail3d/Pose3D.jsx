import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree, useFrame } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import * as THREE from "three";

const USE_TUBES = true;
const JOINT_RADIUS = 0.03;
const LINE_WIDTH = 2;
const TUBE_RADIUS = 0.015;

const EDGES = [
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

const CROSS_EDGES = [
  ["left_shoulder", "right_shoulder"],
  ["left_hip", "right_hip"],
];

const HUD_TARGETS = [
  { key: "shoulder", label: "Shoulder", angleKey: "shoulder_flexion", topPct: 20 },
  { key: "elbow", label: "Elbow", angleKey: "elbow_extension", topPct: 35 },
  { key: "hip", label: "Hip", angleKey: "hip_flexion", topPct: 50 },
  { key: "knee", label: "Knee", angleKey: "knee_flexion", topPct: 65 },
  { key: "ankle", label: "Ankle", angleKey: "ankle_plantarflexion", topPct: 80 },
];

function toVec(j) {
  return new THREE.Vector3(j.x, -j.y, -j.z);
}

function getJoint(frame, side, name) {
  return frame?.position?.[side]?.[name] ?? null;
}

function computeBounds(frame) {
  const pts = [];
  ["left", "right", "mid"].forEach((side) => {
    const g = frame?.position?.[side] ?? {};
    Object.values(g).forEach((j) => pts.push(toVec(j)));
  });

  if (!pts.length) return { center: new THREE.Vector3(), radius: 1 };

  const box = new THREE.Box3().setFromPoints(pts);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const radius = Math.max(size.x, size.y, size.z) * 0.6;

  return { center, radius: Math.max(radius, 0.3) };
}

function BoneTube({ a, b, color, opacity }) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const len = dir.length();
  if (len < 1e-6) return null;

  const mid = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5);
  const quat = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    dir.normalize()
  );

  return (
    <mesh position={mid} quaternion={quat}>
      <cylinderGeometry args={[TUBE_RADIUS, TUBE_RADIUS, len, 8]} />
      <meshStandardMaterial color={color} transparent opacity={opacity} roughness={0.4} />
    </mesh>
  );
}

function FootTriangle({ heel, ankle, toe, color }) {
  const geom = useMemo(() => {
    const g = new THREE.BufferGeometry();
    const verts = new Float32Array([
      heel.x, heel.y, heel.z,
      ankle.x, ankle.y, ankle.z,
      toe.x, toe.y, toe.z,
    ]);
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

function HudConnector({ frame, linesRef }) {
  const { camera, size } = useThree();

  useFrame(() => {
    if (!frame) return;

    ["left", "right"].forEach((side) => {
      HUD_TARGETS.forEach((target) => {
        const lineId = `${side}-${target.key}-line`;
        const lineEl = linesRef.current.get(lineId);
        if (!lineEl) return;

        const fullJointName = `${side}_${target.key}`;
        const jointData = getJoint(frame, side, fullJointName);

        if (jointData) {
          const vec = toVec(jointData);
          vec.project(camera);
          if (vec.z > 1) {
            lineEl.style.opacity = "0";
            return;
          }

          const x = (vec.x * 0.5 + 0.5) * size.width;
          const y = (-(vec.y * 0.5) + 0.5) * size.height;
          const labelX = side === "left" ? size.width - 60 : 60;
          const labelY = size.height * (target.topPct / 100);

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

  return null;
}

function PoseScene({ frame, view, requestFitNonce }) {
  const { camera } = useThree();
  const controlsRef = useRef(null);
  const bounds = useMemo(() => computeBounds(frame), [frame]);

  useEffect(() => {
    const { center, radius } = bounds;
    const fov = camera.fov;
    const dist = (radius / Math.tan((fov * Math.PI) / 360)) * 1.3;

    const pos =
      view === "front"
        ? new THREE.Vector3(center.x, center.y, center.z + dist)
        : view === "side"
          ? new THREE.Vector3(center.x + dist, center.y, center.z)
          : new THREE.Vector3(center.x, center.y + dist, center.z);

    camera.position.copy(pos);
    camera.updateProjectionMatrix();
    if (controlsRef.current) {
      controlsRef.current.target.copy(center);
      controlsRef.current.update();
    }
  }, [requestFitNonce, bounds, camera, view]);

  return (
    <>
      <ambientLight intensity={0.7} />
      <directionalLight position={[2, 3, 2]} intensity={1.2} />

      {["left", "right", "mid"].flatMap((side) =>
        Object.entries(frame?.position?.[side] ?? {}).map(([name, j]) => (
          <mesh key={`${side}:${name}`} position={toVec(j)}>
            <sphereGeometry args={[JOINT_RADIUS]} />
            <meshStandardMaterial
              color={side === "left" ? "#22c55e" : side === "right" ? "#3b82f6" : "#eab308"}
              transparent
              opacity={0.9}
            />
          </mesh>
        ))
      )}

      {EDGES.map(([a, b, side], i) => {
        const ja = getJoint(frame, side, a);
        const jb = getJoint(frame, side, b);
        if (!ja || !jb) return null;
        return USE_TUBES ? (
          <BoneTube key={i} a={toVec(ja)} b={toVec(jb)} color="#9aa7bd" opacity={0.85} />
        ) : (
          <Line key={i} points={[toVec(ja).toArray(), toVec(jb).toArray()]} color="#9aa7bd" lineWidth={LINE_WIDTH} />
        );
      })}

      {CROSS_EDGES.map(([a, b], i) => {
        const ja = getJoint(frame, "left", a);
        const jb = getJoint(frame, "right", b);
        if (!ja || !jb) return null;
        return (
          <Line
            key={`cross-${i}`}
            points={[toVec(ja).toArray(), toVec(jb).toArray()]}
            color="#cbd5e1"
            lineWidth={1}
            opacity={0.6}
          />
        );
      })}

      {["left", "right"].map((side) => {
        const heelJ = getJoint(frame, side, `${side}_heel`);
        const ankleJ = getJoint(frame, side, `${side}_ankle`);
        const toeJ = getJoint(frame, side, `${side}_toe`);
        if (!heelJ || !ankleJ || !toeJ) return null;
        const heel = toVec(heelJ);
        const ankle = toVec(ankleJ);
        const toe = toVec(toeJ);
        const color = side === "left" ? "#22c55e" : "#3b82f6";

        return (
          <group key={`foot-${side}`}>
            <FootTriangle heel={heel} ankle={ankle} toe={toe} color={color} />
            {USE_TUBES ? (
              <>
                <BoneTube a={heel} b={ankle} color={color} opacity={0.95} />
                <BoneTube a={ankle} b={toe} color={color} opacity={0.95} />
                <BoneTube a={toe} b={heel} color={color} opacity={0.95} />
              </>
            ) : (
              <>
                {[
                  [heel, ankle],
                  [ankle, toe],
                  [toe, heel],
                ].map((pts, k) => (
                  <Line key={k} points={[pts[0].toArray(), pts[1].toArray()]} color={color} lineWidth={LINE_WIDTH} />
                ))}
              </>
            )}
          </group>
        );
      })}

      <OrbitControls ref={controlsRef} makeDefault enablePan={false} />
    </>
  );
}

export default function Pose3D({ frame }) {
  const [view, setView] = useState("front");
  const [fitNonce, setFitNonce] = useState(0);
  const linesRef = useRef(new Map());

  useEffect(() => {
    setFitNonce((n) => n + 1);
  }, [view]);

  if (!frame) {
    return <div style={{ color: "#64748b", padding: 24 }}>No Data</div>;
  }

  return (
    <div style={{ width: "100%", height: "100%", position: "relative", overflow: "hidden" }}>
      <div style={{ width: "100%", height: "100%", zIndex: 1 }}>
        <Canvas camera={{ position: [0, 0.3, 2.2], fov: 50 }}>
          <color attach="background" args={["#f7faff"]} />
          <PoseScene frame={frame} view={view} requestFitNonce={fitNonce} />
          <HudConnector frame={frame} linesRef={linesRef} />
        </Canvas>
      </div>

      <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", zIndex: 10, pointerEvents: "none" }}>
        <svg width="100%" height="100%" style={{ position: "absolute", top: 0, left: 0, overflow: "visible" }}>
          {["left", "right"].flatMap((side) =>
            HUD_TARGETS.map((target) => (
              <line
                key={`${side}-${target.key}-line`}
                ref={(el) => {
                  if (el) linesRef.current.set(`${side}-${target.key}-line`, el);
                }}
                stroke={side === "left" ? "#22c55e" : "#3b82f6"}
                strokeWidth="1.5"
                strokeDasharray="4 4"
                opacity="0"
              />
            ))
          )}
        </svg>

        {["left", "right"].map((side) => (
          <div key={side}>
            {HUD_TARGETS.map((target) => {
              const val = frame?.deg?.[side]?.[target.angleKey];
              return (
                <div
                  key={target.key}
                  style={{
                    position: "absolute",
                    top: `${target.topPct}%`,
                    [side === "left" ? "right" : "left"]: "20px",
                    width: "80px",
                    transform: "translateY(-50%)",
                    background: "#ffffff",
                    border: `1px solid ${side === "left" ? "#34d399" : "#60a5fa"}`,
                    borderRadius: "6px",
                    padding: "6px 10px",
                    color: "#1e293b",
                    textAlign: side === "left" ? "right" : "left",
                    pointerEvents: "auto",
                    boxShadow: "0 6px 14px rgba(15,23,42,0.08)",
                  }}
                >
                  <div style={{ fontSize: "18px", fontWeight: "bold", lineHeight: 1 }}>
                    {typeof val === "number" ? val.toFixed(0) : "-"}°
                  </div>
                  <div style={{ fontSize: "10px", color: "#64748b", marginTop: 2, textTransform: "uppercase" }}>
                    {target.label}
                  </div>
                </div>
              );
            })}
          </div>
        ))}

        <div style={{ position: "absolute", top: 12, left: 12, display: "flex", gap: 8, pointerEvents: "auto" }}>
          {["front", "side", "top"].map((v) => (
            <button key={v} onClick={() => setView(v)} style={btn(view === v)}>
              {v}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function btn(active) {
  return {
    padding: "6px 10px",
    borderRadius: 10,
    background: active ? "#e0e7ff" : "#ffffff",
    color: "#1e293b",
    border: "1px solid #dbe3f3",
    cursor: "pointer",
    textTransform: "capitalize",
    fontSize: "12px",
    fontWeight: 500,
  };
}
