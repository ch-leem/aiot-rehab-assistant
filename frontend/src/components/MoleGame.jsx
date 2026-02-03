import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import "./MoleGame.css";

export default function MoleGame({
  onCountChange,
  requiredPower = 0.8,
  showLoadingOverlay = true,
  tryStartSignal = 0,
  onPowerChange = null,
}) {
  const containerRef = useRef(null);
  const [gameState, setGameState] = useState("ready");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);
  const gameStateRef = useRef("ready");
  const moleRef = useRef(null);
  const hammerRef = useRef(null);
  const onCountChangeRef = useRef(onCountChange);
  const initializedRef = useRef(false);
  const loadStartRef = useRef(0);
  const loadingDelayRef = useRef(null);
  const assetsReadyRef = useRef(false);
  const assetsTimeoutRef = useRef(null);
  const tryActiveRef = useRef(false);
  const startTryRef = useRef(null);
  const powerRef = useRef(null);

  onCountChangeRef.current = onCountChange;

  const handleRetry = () => {
    setLoadError(false);
    setLoading(true);
    initializedRef.current = false;
    setRetryKey((prev) => prev + 1);
  };

  useEffect(() => {
    if (!containerRef.current || initializedRef.current) return;
    initializedRef.current = true;
    setLoading(true);
    setLoadError(false);
    loadStartRef.current = performance.now();
    assetsReadyRef.current = false;

    const container = containerRef.current;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight || 500);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x87ceeb);

    const camera = new THREE.PerspectiveCamera(
      60,
      container.clientWidth / (container.clientHeight || 500),
      1,
      30000
    );
    const controls = new OrbitControls(camera, renderer.domElement);

    camera.position.set(12.542357828590571, 7.304516962830691, 13.29922596992769);
    controls.target.set(-2.3569183892997163, 5.445169949849723, 4.009778652053535);
    controls.enableRotate = false;
    controls.enablePan = false;
    controls.enableZoom = true;
    controls.update();

    const sun = new THREE.DirectionalLight(0xffffff, 1.5);
    sun.position.set(200, 2000, 200);
    scene.add(sun);
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));

    const loader = new GLTFLoader();
    const loadingTimeout = setTimeout(() => {
      const elapsed = performance.now() - loadStartRef.current;
      const delay = Math.max(0, 3000 - elapsed);
      if (loadingDelayRef.current) {
        clearTimeout(loadingDelayRef.current);
      }
      loadingDelayRef.current = setTimeout(() => {
        setLoadError(true);
        setLoading(false);
      }, delay);
    }, 10000);

    let currentRound = 0;
    const totalRounds = 10;
    const popDuration = 0.5;
    const baseShowDuration = 14.0;
    const firstShowDuration = 30.0;
    let moleTimer = 0;
    let showTimer = 0;
    let phase = "idle";
    let hitTriggered = false;
    let tryResolved = false;
    let holdStart = 0;
    let holding = false;

    const beginTry = () => {
      moleTimer = 0;
      showTimer = 0;
      phase = "popUp";
      hitTriggered = false;
      tryResolved = false;
      tryActiveRef.current = false;
      startTryRef.current = () => {
        moleTimer = 0;
        showTimer = 0;
        phase = "popUp";
        hitTriggered = false;
        tryResolved = false;
        tryActiveRef.current = true;
      };
    };

    loader.load(
      "/mole7.glb",
      (gltf) => {
        clearTimeout(loadingTimeout);
        const root = gltf.scene;
        scene.add(root);

        let moleRoot = null;
        let hammerRoot = null;

        const hasRenderableMeshes = (target) => {
          if (!target) return false;
          let meshCount = 0;
          target.traverse((obj) => {
            if (obj.isMesh) meshCount += 1;
          });
          if (meshCount === 0) return false;
          const bounds = new THREE.Box3().setFromObject(target);
          const size = bounds.getSize(new THREE.Vector3());
          return (
            Number.isFinite(size.x) &&
            Number.isFinite(size.y) &&
            Number.isFinite(size.z) &&
            size.x + size.y + size.z > 0
          );
        };

        root.traverse((obj) => {
          if (obj.isMesh) {
            obj.castShadow = true;
            obj.receiveShadow = true;
          }
          if (obj.name === "Mole") moleRoot = obj;
          if (obj.name === "Hammer") hammerRoot = obj;
          if (!hammerRoot && obj.name === "Cilindro.007_molesAtlas_0") {
            hammerRoot = obj.parent?.parent ?? obj.parent ?? obj;
          }
        });

        if (!moleRoot) {
          root.traverse((obj) => {
            if (!moleRoot && obj.name && obj.name.startsWith("Mole")) {
              moleRoot = obj;
            }
          });
        }

        if (moleRoot) {
          moleRoot.userData.originalY = moleRoot.position.y;
          moleRoot.userData.hiddenY = moleRoot.position.y - 1200;
          moleRoot.position.y = moleRoot.userData.hiddenY;
          moleRef.current = moleRoot;
        }

        if (hammerRoot) {
          hammerRoot.userData.originalY = hammerRoot.position.y;
          hammerRoot.userData.hiddenY = hammerRoot.position.y + 800;
          hammerRoot.userData.hitY = hammerRoot.position.y - 250;
          hammerRoot.position.y = hammerRoot.userData.hiddenY;
          hammerRoot.visible = false;
          hammerRef.current = hammerRoot;
        }

        gameStateRef.current = "playing";
        setGameState("playing");
        beginTry();
        assetsReadyRef.current = Boolean(
          moleRef.current &&
            hammerRef.current &&
            hasRenderableMeshes(moleRef.current) &&
            hasRenderableMeshes(hammerRef.current)
        );
        if (assetsTimeoutRef.current) {
          clearTimeout(assetsTimeoutRef.current);
        }
        assetsTimeoutRef.current = setTimeout(() => {
          if (!assetsReadyRef.current) {
            setLoadError(true);
            setLoading(false);
          }
        }, 6000);
        const elapsed = performance.now() - loadStartRef.current;
        const delay = Math.max(0, 3000 - elapsed);
        if (loadingDelayRef.current) {
          clearTimeout(loadingDelayRef.current);
        }
        loadingDelayRef.current = setTimeout(() => {
          if (assetsReadyRef.current) {
            setLoading(false);
            setLoadError(false);
          }
        }, delay);
      },
      undefined,
      () => {
        clearTimeout(loadingTimeout);
        const elapsed = performance.now() - loadStartRef.current;
        const delay = Math.max(0, 3000 - elapsed);
        if (loadingDelayRef.current) {
          clearTimeout(loadingDelayRef.current);
        }
        loadingDelayRef.current = setTimeout(() => {
          setLoadError(true);
          setLoading(false);
        }, delay);
      }
    );

    const hitMole = () => {
      const mole = moleRef.current;
      const hammer = hammerRef.current;
      if (!mole || !hammer || tryResolved) return;
      tryResolved = true;

      const createHitEffect = (moleObj, scale = 1) => {
        const particles = [];
        const parentObj = moleObj.parent || scene;

        // ✅ 1. 폭발 링
        const ringCount = 3;
        for (let r = 0; r < ringCount; r++) {
          const ringGeometry = new THREE.RingGeometry(10 * scale, 15 * scale, 16);
          const ringMaterial = new THREE.MeshBasicMaterial({
            color: r === 0 ? 0xffff00 : r === 1 ? 0xffa500 : 0xff6600,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
          });
          const ring = new THREE.Mesh(ringGeometry, ringMaterial);
          ring.position.set(moleObj.position.x, moleObj.position.y + 80 * scale, moleObj.position.z);
          ring.rotation.x = Math.PI / 2;
          ring.userData.expandSpeed = 80 + r * 20;
          ring.userData.type = 'ring';
          parentObj.add(ring);
          particles.push(ring);
        }

        // ✅ 2. 별 파티클
        const starCount = 12;
        for (let i = 0; i < starCount; i++) {
          const angle = (Math.PI * 2 * i) / starCount;
          const starShape = new THREE.Shape();
          const outerRadius = 15 * scale;
          const innerRadius = 7 * scale;
          
          for (let j = 0; j < 10; j++) {
            const a = (j * Math.PI) / 5;
            const r = j % 2 === 0 ? outerRadius : innerRadius;
            const x = Math.cos(a) * r;
            const y = Math.sin(a) * r;
            if (j === 0) starShape.moveTo(x, y);
            else starShape.lineTo(x, y);
          }
          starShape.closePath();
          
          const starGeometry = new THREE.ShapeGeometry(starShape);
          const starMaterial = new THREE.MeshBasicMaterial({
            color: 0xffff00,
            transparent: true,
            opacity: 1,
            blending: THREE.AdditiveBlending,
          });
          const star = new THREE.Mesh(starGeometry, starMaterial);
          star.position.set(
            moleObj.position.x,
            moleObj.position.y + 100 * scale,
            moleObj.position.z
          );
          star.userData.velocity = new THREE.Vector3(
            Math.cos(angle) * 60 * scale,
            (Math.random() * 30 + 40) * scale,
            Math.sin(angle) * 60 * scale
          );
          star.userData.rotSpeed = (Math.random() - 0.5) * 0.3;
          star.userData.type = 'star';
          parentObj.add(star);
          particles.push(star);
        }

        // ✅ 3. 구형 파티클
        const sphereCount = 16;
        for (let i = 0; i < sphereCount; i++) {
          const size = (Math.random() * 10 + 15) * scale;
          const geometry = new THREE.SphereGeometry(size, 8, 8);
          const material = new THREE.MeshBasicMaterial({
            color: i % 2 === 0 ? 0xffd700 : 0xff8c00,
            transparent: true,
            opacity: 0.9,
            blending: THREE.AdditiveBlending,
          });
          const sphere = new THREE.Mesh(geometry, material);
          sphere.position.set(
            moleObj.position.x + (Math.random() - 0.5) * 30 * scale,
            moleObj.position.y + 100 * scale,
            moleObj.position.z + (Math.random() - 0.5) * 30 * scale
          );
          sphere.userData.velocity = new THREE.Vector3(
            (Math.random() - 0.5) * 80 * scale,
            (Math.random() * 60 + 50) * scale,
            (Math.random() - 0.5) * 80 * scale
          );
          sphere.userData.type = 'sphere';
          parentObj.add(sphere);
          particles.push(sphere);
        }

        // ✅ 4. 번개 라인
        const lightningCount = 8;
        for (let i = 0; i < lightningCount; i++) {
          const angle = (Math.PI * 2 * i) / lightningCount;
          const points = [];
          const length = 80 * scale;
          for (let j = 0; j <= 5; j++) {
            const t = j / 5;
            points.push(new THREE.Vector3(
              Math.cos(angle) * length * t + (Math.random() - 0.5) * 10 * scale,
              100 * scale + (Math.random() - 0.5) * 20 * scale,
              Math.sin(angle) * length * t + (Math.random() - 0.5) * 10 * scale
            ));
          }
          const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
          const lineMaterial = new THREE.LineBasicMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: 1,
            linewidth: 3,
            blending: THREE.AdditiveBlending,
          });
          const line = new THREE.Line(lineGeometry, lineMaterial);
          line.position.set(moleObj.position.x, moleObj.position.y, moleObj.position.z);
          line.userData.type = 'lightning';
          line.userData.life = 0;
          parentObj.add(line);
          particles.push(line);
        }

        // ✅ 애니메이션
        const startTime = performance.now();
        const animateParticles = () => {
          const elapsed = performance.now() - startTime;
          const progress = elapsed / 800;
          let alive = false;

          particles.forEach((p) => {
            if (p.userData.type === 'ring') {
              p.scale.x += p.userData.expandSpeed * 0.016;
              p.scale.y += p.userData.expandSpeed * 0.016;
              p.material.opacity = Math.max(0, 1 - progress * 1.5);
              if (p.material.opacity > 0) alive = true;
            } else if (p.userData.type === 'star') {
              p.position.add(p.userData.velocity.clone().multiplyScalar(0.016));
              p.userData.velocity.y -= 3;
              p.rotation.z += p.userData.rotSpeed;
              p.material.opacity = Math.max(0, 1 - progress * 1.2);
              if (p.material.opacity > 0) alive = true;
            } else if (p.userData.type === 'sphere') {
              p.position.add(p.userData.velocity.clone().multiplyScalar(0.016));
              p.userData.velocity.y -= 4;
              p.scale.multiplyScalar(0.96);
              p.material.opacity = Math.max(0, 1 - progress * 1.3);
              if (p.material.opacity > 0) alive = true;
            } else if (p.userData.type === 'lightning') {
              p.userData.life += 0.016;
              p.material.opacity = Math.max(0, 1 - p.userData.life * 5);
              if (p.material.opacity > 0) alive = true;
            }
          });

          if (alive && progress < 1.5) {
            requestAnimationFrame(animateParticles);
          } else {
            particles.forEach((p) => {
              if (p.parent) p.parent.remove(p);
              if (p.geometry) p.geometry.dispose();
              if (p.material) p.material.dispose();
            });
          }
        };

        animateParticles();
      };

      hammer.visible = true;
      const hStartTime = performance.now();

      const animateHammer = (now) => {
        const elapsed = now - hStartTime;
        const progress = Math.min(1, elapsed / 250);
        hammer.position.y = THREE.MathUtils.lerp(
          hammer.userData.hiddenY,
          hammer.userData.hitY,
          progress * progress
        );

        if (progress < 1) {
          requestAnimationFrame(animateHammer);
        } else {
          // ✅ 이펙트 생성!
          createHitEffect(mole, 1);
          
          const mStartTime = performance.now();
          const startY = mole.position.y;
          const targetY = mole.userData.hiddenY;

          const animateMoleDown = (mNow) => {
            const mElapsed = mNow - mStartTime;
            const mProgress = Math.min(1, mElapsed / 300);
            mole.position.y = THREE.MathUtils.lerp(startY, targetY, mProgress);
            if (mProgress < 1) requestAnimationFrame(animateMoleDown);
          };
          requestAnimationFrame(animateMoleDown);
        }
      };
      requestAnimationFrame(animateHammer);

      setTimeout(() => {
        if (hammerRef.current) {
          hammerRef.current.visible = false;
          hammerRef.current.position.y = hammerRef.current.userData.hiddenY;
        }
        currentRound += 1;
        if (onCountChangeRef.current) onCountChangeRef.current(currentRound, totalRounds);
        if (currentRound >= totalRounds) {
          gameStateRef.current = "completed";
          setGameState("completed");
        } else {
          beginTry();
        }
      }, 1000);
    };

    const onKeyDown = (e) => {
      if (e.code === "KeyW" && !holding && gameStateRef.current === "playing") {
        holding = true;
        holdStart = performance.now();
      }
    };
    const onKeyUp = (e) => {
      if (e.code === "KeyW") {
        holding = false;
        holdStart = 0;
      }
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    const poseSseUrl = import.meta.env.VITE_POSE_SSE_URL || "/api/ingest/events";
    let poseStream = null;
    if (poseSseUrl && typeof EventSource !== "undefined") {
      try {
        poseStream = new EventSource(poseSseUrl);
        poseStream.onmessage = (ev) => {
          try {
            const payload = JSON.parse(ev.data);
            console.log("[SSE] lower-body payload", payload);
            const frames = Array.isArray(payload?.frames) ? payload.frames : [];
            const frame = frames.length ? frames[frames.length - 1] : null;
            const rawPower = frame?.sensor?.power;
            const parsedPower = Number(rawPower);
            if (Number.isFinite(parsedPower)) {
              powerRef.current = parsedPower;
              if (typeof onPowerChange === "function") {
                onPowerChange(parsedPower);
              }
            }
          } catch {
            // ignore parse errors
          }
        };
        poseStream.onerror = () => {
          // ignore stream errors
        };
      } catch {
        // ignore stream errors
      }
    }

    let rafId;
    const animate = () => {
      rafId = requestAnimationFrame(animate);
      const dt = 0.016;

      if (gameStateRef.current === "playing" && moleRef.current) {
        if (!tryActiveRef.current) {
          renderer.render(scene, camera);
          return;
        }
        moleTimer += dt;
        if (phase === "popUp") {
          const p = Math.min(1, moleTimer / popDuration);
          moleRef.current.position.y = THREE.MathUtils.lerp(
            moleRef.current.userData.hiddenY,
            moleRef.current.userData.originalY,
            p
          );
          if (p >= 1) {
            phase = "show";
            showTimer = 0;
          }
        } else if (phase === "show") {
          showTimer += dt;
          const isFirstTry = currentRound === 0;
          const maxShowDuration = isFirstTry ? firstShowDuration : baseShowDuration;
          if (showTimer >= maxShowDuration && !hitTriggered && !tryResolved) {
            hitTriggered = true;
            tryResolved = true;
            const startY = moleRef.current.position.y;
            const targetY = moleRef.current.userData.hiddenY;
            const mStartTime = performance.now();
            const failAnim = (mNow) => {
              const mp = Math.min(1, (mNow - mStartTime) / 400);
              moleRef.current.position.y = THREE.MathUtils.lerp(startY, targetY, mp);
              if (mp < 1) requestAnimationFrame(failAnim);
              else {
                currentRound += 1;
                if (onCountChangeRef.current) onCountChangeRef.current(currentRound, totalRounds);
                if (currentRound >= totalRounds) {
                  gameStateRef.current = "completed";
                  setGameState("completed");
                } else {
                  beginTry();
                }
              }
            };
            requestAnimationFrame(failAnim);
          }
          if (holding && !hitTriggered && !tryResolved && performance.now() - holdStart >= 1000) {
            hitTriggered = true;
            hitMole();
          }
          const realtimePower = powerRef.current;
          if (!hitTriggered && !tryResolved && realtimePower != null && realtimePower >= requiredPower) {
            hitTriggered = true;
            hitMole();
          }
        }
      }
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      clearTimeout(loadingTimeout);
      if (loadingDelayRef.current) {
        clearTimeout(loadingDelayRef.current);
        loadingDelayRef.current = null;
      }
      if (assetsTimeoutRef.current) {
        clearTimeout(assetsTimeoutRef.current);
        assetsTimeoutRef.current = null;
      }
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      if (poseStream) {
        poseStream.close();
      }
      cancelAnimationFrame(rafId);
      initializedRef.current = false;
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      scene.clear();
    };
  }, [retryKey]);

  useEffect(() => {
    if (!startTryRef.current) return;
    startTryRef.current();
  }, [tryStartSignal]);

  return (
    <div
      className="mole-game-wrapper"
      style={{ width: "100%", height: "100%", position: "relative" }}
    >
      <div
        ref={containerRef}
        className="mole-game-container"
        style={{ width: "100%", height: "100%" }}
      />
      {showLoadingOverlay && loading && (
        <div className="loading-overlay">
          <div className="mole-hole">
            <div className="digging-mole" />
          </div>
          <p className="loading-text">열심히 굴 파는 중...</p>
        </div>
      )}
      {showLoadingOverlay && loadError && (
        <div className="loading-overlay">
          <p style={{ color: "#d32f2f", fontWeight: "bold" }}>
            ⚠️ 굴 파기에 실패했습니다.
          </p>
          <button
            onClick={handleRetry}
            className="retry-btn"
            style={{ marginTop: "10px" }}
            type="button"
          >
            다시 시도
          </button>
        </div>
      )}
      {gameState === "completed" && null}
    </div>
  );
}
