import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import "./MoleGame.css";

export default function MoleGame({
  onCountChange,
  sensorPower = null,
  requiredPower = 0.8,
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

  onCountChangeRef.current = onCountChange;

  const handleRetry = () => {
    setLoadError(false);
    setLoading(true);
    initializedRef.current = false;
    setRetryKey((prev) => prev + 1);
  };

  useEffect(() => {
    // 1. 초기화 방어막: StrictMode 등에서 두 번 실행되는 것 방지
    if (!containerRef.current || initializedRef.current) return;
    initializedRef.current = true;
    setLoading(true);
    setLoadError(false);
    loadStartRef.current = performance.now();
    assetsReadyRef.current = false;

    const container = containerRef.current;
    
    // 2. 렌더러 생성 및 설정
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight || 500);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x87ceeb);

    // 3. 카메라 및 컨트롤 고정 (사용자 요청 좌표)
    const camera = new THREE.PerspectiveCamera(60, container.clientWidth / (container.clientHeight || 500), 1, 30000);
    const controls = new OrbitControls(camera, renderer.domElement);

    camera.position.set(12.542357828590571, 7.304516962830691, 13.29922596992769);
    controls.target.set(-2.3569183892997163, 5.445169949849723, 4.009778652053535);
    controls.enableRotate = false;
    controls.enablePan = false;
    controls.enableZoom = false;
    controls.update();

    // 4. 조명 설정
    const sun = new THREE.DirectionalLight(0xffffff, 1.5);
    sun.position.set(200, 2000, 200); // 좌표가 크므로 조명도 높게
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

    // 게임 변수
    let currentRound = 0;
    const totalRounds = 10;
    const popDuration = 0.5;
    const baseShowDuration = 5.0;
    const firstShowDuration = 30.0;
    let moleTimer = 0;
    let showTimer = 0;
    let phase = "idle";
    let hitTriggered = false;
    let tryResolved = false;
    let holdStart = 0;
    let holding = false;

    // 5. 모델 로딩 (안정적인 Traverse 로직)
    loader.load("/mole7.glb", (gltf) => {
      clearTimeout(loadingTimeout);
      const root = gltf.scene;
      scene.add(root);

      let moleRoot = null;
      let hammerRoot = null;

      root.traverse((obj) => {
        if (obj.isMesh) {
          obj.castShadow = true;
          obj.receiveShadow = true;
        }
        // 정확한 최상위 이름 매칭
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
      } else {
        console.error("[MoleGame] Mole root not found");
      }

      if (hammerRoot) {
        hammerRoot.userData.originalY = hammerRoot.position.y;
        hammerRoot.userData.hiddenY = hammerRoot.position.y + 800; 
        // ✅ 요청하신 대로 망치가 더 깊게(-450) 내려가도록 수정
        hammerRoot.userData.hitY = hammerRoot.position.y - 250;    
        hammerRoot.position.y = hammerRoot.userData.hiddenY;
        hammerRoot.visible = false;
        hammerRef.current = hammerRoot;
      } else {
        console.error("[MoleGame] Hammer root not found");
      }

      gameStateRef.current = "playing";
      setGameState("playing");
      beginTry();
      assetsReadyRef.current = Boolean(moleRef.current && hammerRef.current);
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
    }, undefined, (error) => {
      clearTimeout(loadingTimeout);
      console.error("모델 로딩 실패:", error);
      const elapsed = performance.now() - loadStartRef.current;
      const delay = Math.max(0, 3000 - elapsed);
      if (loadingDelayRef.current) {
        clearTimeout(loadingDelayRef.current);
      }
      loadingDelayRef.current = setTimeout(() => {
        setLoadError(true);
        setLoading(false);
      }, delay);
    });

    const beginTry = () => {
      moleTimer = 0;
      showTimer = 0;
      phase = "popUp";
      hitTriggered = false;
      tryResolved = false;
      console.log(`[MoleGame] try start ${currentRound + 1}/${totalRounds}`);
    };

    // 6. 타격 함수
    const hitMole = () => {
      const mole = moleRef.current;
      const hammer = hammerRef.current;
      if (!mole || !hammer || tryResolved) return;
      tryResolved = true;

      currentRound += 1;
      if (onCountChangeRef.current) onCountChangeRef.current(currentRound, totalRounds);
      console.log(`[MoleGame] try success ${currentRound}/${totalRounds}`);

      const createHitEffect = (pos) => {
        const particleCount = 8;
        const particles = [];
        const geometry = new THREE.SphereGeometry(12, 10, 10);
        const material = new THREE.MeshBasicMaterial({
          color: 0xffd700,
          transparent: true,
          opacity: 0.9,
          blending: THREE.AdditiveBlending,
        });

        for (let i = 0; i < particleCount; i += 1) {
          const p = new THREE.Mesh(geometry, material);
          p.position.copy(pos);
          p.position.y += 150;
          p.frustumCulled = false;
          p.renderOrder = 10;
          p.userData.velocity = new THREE.Vector3(
            (Math.random() - 0.5) * 50,
            Math.random() * 50 + 20,
            (Math.random() - 0.5) * 50
          );
          scene.add(p);
          particles.push(p);
        }

        const animateParticles = () => {
          let alive = false;
          particles.forEach((p) => {
            p.position.add(p.userData.velocity);
            p.userData.velocity.y -= 2;
            p.scale.multiplyScalar(0.95);
            if (p.scale.x > 0.1) {
              alive = true;
            } else {
              p.visible = false;
            }
          });

          if (alive) {
            requestAnimationFrame(animateParticles);
          } else {
            particles.forEach((p) => scene.remove(p));
          }
        };

        animateParticles();
      };

      hammer.visible = true;
      const hStartTime = performance.now();
      
      const animateHammer = (now) => {
        const elapsed = now - hStartTime;
        const progress = Math.min(1, elapsed / 250);
        hammer.position.y = THREE.MathUtils.lerp(hammer.userData.hiddenY, hammer.userData.hitY, progress * progress);

        if (progress < 1) {
          requestAnimationFrame(animateHammer);
        } else {
          createHitEffect(mole.position);
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
        if (currentRound >= totalRounds) {
          gameStateRef.current = "completed";
          setGameState("completed");
        } else {
          beginTry();
        }
      }, 1500);
    };

    // 7. 키보드 이벤트
    const onKeyDown = (e) => { 
      if (e.code === "KeyW" && !holding && gameStateRef.current === "playing") { 
        holding = true; holdStart = performance.now(); 
      } 
    };
    const onKeyUp = (e) => { if (e.code === "KeyW") { holding = false; holdStart = 0; } };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    // 8. 메인 애니메이션 루프
    let rafId;
    const animate = () => {
      rafId = requestAnimationFrame(animate);
      const dt = 0.016;

      if (gameStateRef.current === "playing" && moleRef.current) {
        moleTimer += dt;
        if (phase === "popUp") {
          const p = Math.min(1, moleTimer / popDuration);
          moleRef.current.position.y = THREE.MathUtils.lerp(moleRef.current.userData.hiddenY, moleRef.current.userData.originalY, p);
          if (p >= 1) { phase = "show"; showTimer = 0; }
        } 
        else if (phase === "show") {
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
                console.log(`[MoleGame] try fail ${currentRound}/${totalRounds}`);
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
          if (holding && !hitTriggered && !tryResolved && (performance.now() - holdStart >= 1000)) { 
            hitTriggered = true; 
            hitMole(); 
          }
          if (
            !hitTriggered &&
            !tryResolved &&
            sensorPower != null &&
            sensorPower >= requiredPower
          ) {
            hitTriggered = true;
            hitMole();
          }
        }
      }
      renderer.render(scene, camera);
    };
    animate();

    // 9. 클린업 (중요!)
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
      cancelAnimationFrame(rafId);
      initializedRef.current = false;
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      scene.clear();
    };
  }, [retryKey]);

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
      {loading && (
        <div className="loading-overlay">
          <div className="mole-hole">
            <div className="digging-mole" />
          </div>
          <p className="loading-text">열심히 굴 파는 중...</p>
        </div>
      )}
      {loadError && (
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
