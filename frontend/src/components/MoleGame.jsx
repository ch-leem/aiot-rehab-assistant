import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import "./MoleGame.css";

export default function MoleGame({ onCountChange, patientWeight = 70 }) {
  const containerRef = useRef(null);
  const [gameState, setGameState] = useState("ready");
  const gameStateRef = useRef("ready");

  const setGameStateSafe = (next) => {
    gameStateRef.current = next;
    setGameState(next);
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    const getSize = () => {
      const w = container.clientWidth || 1;
      const h = container.clientHeight || 1;
      return [w, Math.max(360, h)];
    };
    const [initW, initH] = getSize();
    renderer.setSize(initW, initH);
    renderer.shadowMap.enabled = true;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x87ceeb);

    const camera = new THREE.PerspectiveCamera(60, initW / initH, 0.1, 1000);
    camera.position.set(0, 15, 25);
    camera.lookAt(0, 0, 0);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.enableRotate = true;
    controls.enableZoom = true;
    controls.minDistance = 15;
    controls.maxDistance = 40;
    controls.target.set(0, 0, 0);
    controls.update();

    const sun = new THREE.DirectionalLight(0xffffff, 1.5);
    sun.position.set(10, 20, 10);
    sun.castShadow = true;
    sun.shadow.camera.left = -30;
    sun.shadow.camera.right = 30;
    sun.shadow.camera.top = 30;
    sun.shadow.camera.bottom = -30;
    scene.add(sun);
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));

    let currentRound = 0;
    const totalRounds = 10;
    let moleUpTime = 0;
    const moleDisplayDuration = 5;
    let currentMole = null;
    let hammer = null;
    let isHammerAnimating = false;

    let currentPower = 0;
    let requiredPower = patientWeight * 0.8;

    const loader = new GLTFLoader();
    let moleScene = null;
    const moles = [];

    loader.load(
      "/mole_game.glb",
      (gltf) => {
        moleScene = gltf.scene;
        scene.add(moleScene);

        moleScene.traverse((obj) => {
          if (obj.isMesh) {
            obj.castShadow = true;
            obj.receiveShadow = true;
          }
        });

        moleScene.traverse((obj) => {
          if (obj.name && obj.name.startsWith("Body")) {
            moles.push(obj);
            obj.visible = false;
          }
        });

        const hammerGeo = new THREE.CylinderGeometry(0.5, 0.5, 3, 8);
        const hammerMat = new THREE.MeshStandardMaterial({ color: 0x8b4513 });
        hammer = new THREE.Mesh(hammerGeo, hammerMat);
        hammer.position.set(0, 10, 0);
        hammer.rotation.z = Math.PI / 4;
        hammer.visible = false;
        scene.add(hammer);

        startNextRound();
      },
      undefined,
      (err) => {
        console.error("GLB load failed", err);
      }
    );

    const startNextRound = () => {
      if (currentRound >= totalRounds) {
        setGameStateSafe("completed");
        if (typeof onCountChange === "function") {
          onCountChange(totalRounds, totalRounds);
        }
        return;
      }

      currentRound += 1;
      setGameStateSafe("playing");

      if (moles.length > 0) {
        const randomIndex = Math.floor(Math.random() * moles.length);
        currentMole = moles[randomIndex];
        currentMole.visible = true;

        if (!currentMole.userData.originalY) {
          currentMole.userData.originalY = currentMole.position.y;
          currentMole.userData.hiddenY = currentMole.position.y - 2;
        }

        currentMole.position.y = currentMole.userData.hiddenY;
      }

      moleUpTime = 0;

      if (typeof onCountChange === "function") {
        onCountChange(currentRound - 1, totalRounds);
      }
    };

    const hitMole = () => {
      if (!currentMole || isHammerAnimating) return;

      isHammerAnimating = true;
      if (hammer && currentMole) {
        hammer.visible = true;
        hammer.position.set(
          currentMole.position.x,
          currentMole.position.y + 3,
          currentMole.position.z
        );

        playHitSound();
      }

      setTimeout(() => {
        if (currentMole) {
          currentMole.visible = false;
        }
        if (hammer) {
          hammer.visible = false;
        }
        isHammerAnimating = false;
        startNextRound();
      }, 500);
    };

    let audioCtx = null;
    const playHitSound = () => {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state !== "running") return;

      const now = audioCtx.currentTime;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(600, now);
      osc.frequency.exponentialRampToValueAtTime(200, now + 0.1);

      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.3, now + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.15);

      osc.connect(gain);
      gain.connect(audioCtx.destination);

      osc.start(now);
      osc.stop(now + 0.15);
    };

    const sseUrl = import.meta.env.VITE_POSE_SSE_URL || "/api/ingest/events";
    let sseStream = null;

    if (typeof EventSource !== "undefined") {
      try {
        sseStream = new EventSource(sseUrl);
        sseStream.onmessage = (ev) => {
          try {
            const payload = JSON.parse(ev.data);
            const frames = Array.isArray(payload?.frames) ? payload.frames : [];
            const frame = frames.length ? frames[frames.length - 1] : null;

            if (frame && frame.sensor && typeof frame.sensor.power === "number") {
              currentPower = frame.sensor.power;
              requiredPower = patientWeight * 0.8;

              if (currentPower >= requiredPower && currentMole && !isHammerAnimating) {
                hitMole();
              }
            }
          } catch (err) {
            console.error("SSE parse error:", err);
          }
        };

        sseStream.onerror = () => {
          console.warn("SSE connection error");
        };
      } catch (err) {
        console.error("SSE setup error:", err);
      }
    }

    const clock = new THREE.Clock();
    let rafId = 0;

    const animate = () => {
      rafId = requestAnimationFrame(animate);
      const dt = Math.min(0.033, clock.getDelta());

      if (gameStateRef.current === "playing" && currentMole) {
        moleUpTime += dt;

        if (moleUpTime < 0.5) {
          const progress = moleUpTime / 0.5;
          const eased = 1 - Math.pow(1 - progress, 3);
          currentMole.position.y = THREE.MathUtils.lerp(
            currentMole.userData.hiddenY,
            currentMole.userData.originalY,
            eased
          );
        }

        if (moleUpTime >= moleDisplayDuration) {
          if (currentMole) {
            currentMole.visible = false;
          }
          startNextRound();
        }
      }

      if (isHammerAnimating && hammer) {
        hammer.rotation.z += dt * 10;
        hammer.position.y -= dt * 15;
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    const resize = () => {
      const [w, h] = getSize();
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);

    return () => {
      if (sseStream) {
        sseStream.close();
      }
      resizeObserver.disconnect();
      cancelAnimationFrame(rafId);
      controls.dispose();
      renderer.dispose();
      scene.clear();
      if (audioCtx && audioCtx.state !== "closed") {
        audioCtx.close();
      }
      if (renderer.domElement.parentElement) {
        renderer.domElement.parentElement.removeChild(renderer.domElement);
      }
    };
  }, [patientWeight, onCountChange]);

  return (
    <div className="mole-game-wrapper">
      <div ref={containerRef} className="mole-game-container" />
      {gameState === "completed" && (
        <div className="game-complete-overlay">
          <h2>운동 완료! 🎉</h2>
          <p>10회 모두 완료하셨습니다.</p>
        </div>
      )}
    </div>
  );
}
