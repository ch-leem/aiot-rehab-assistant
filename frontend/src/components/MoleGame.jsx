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

    const camera = new THREE.PerspectiveCamera(60, container.clientWidth / (container.clientHeight || 500), 1, 30000);
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
    const baseShowDuration = 5.0;
    const firstShowDuration = 30.0;
    let showTimer = 0;
    let phase = "show";  // ✅ 처음부터 show!
    let hitTriggered = false;
    let tryResolved = false;
    let holdStart = 0;
    let holding = false;

    loader.load("/mole7.glb", (gltf) => {
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
        return Number.isFinite(size.x) && Number.isFinite(size.y) && Number.isFinite(size.z) && (size.x + size.y + size.z) > 0;
      };

      root.traverse((obj) => {
        if (obj.isMesh) {
          obj.castShadow = true;
          obj.receiveShadow = true;
        }
        
        // ✅ Mole을 찾되, 그룹 전체를 찾음!
        if (obj.name === "Mole") {
          // Mole이 메시인지 그룹인지 확인
          if (obj.type === "Group" || obj.children.length > 0) {
            console.log(`[MoleGame] 🐹 Mole 그룹 발견`);
            moleRoot = obj;
          } else {
            console.log(`[MoleGame] 🐹 Mole 메시 발견 (부모 찾기)`);
            // 메시라면 부모를 Mole로
            moleRoot = obj.parent && obj.parent.name === "Mole" ? obj.parent : obj;
          }
        }
        
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
        // ✅ 처음에는 나와있는 상태! (position.y 변경 안 함!)
        moleRef.current = moleRoot;
        console.log(`[MoleGame] 🐹 두더지 Y=${moleRoot.position.y.toFixed(2)} (나와있음)`);
      } else {
        console.error("[MoleGame] Mole root not found");
      }

      if (hammerRoot) {
        hammerRoot.userData.originalY = hammerRoot.position.y;
        hammerRoot.userData.hiddenY = hammerRoot.position.y + 800; 
        hammerRoot.userData.hitY = hammerRoot.position.y - 250;    
        hammerRoot.position.y = hammerRoot.userData.hiddenY;
        hammerRoot.visible = false;
        hammerRef.current = hammerRoot;
        console.log(`[MoleGame] 🔨 망치 준비 완료`);
      } else {
        console.error("[MoleGame] Hammer root not found");
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
      showTimer = 0;
      phase = "show";  // ✅ 바로 show 상태! (이미 나와있음)
      hitTriggered = false;
      tryResolved = false;
      console.log(`[MoleGame] 시작 ${currentRound + 1}/${totalRounds} - 두더지 대기 중`);
    };

    const hitMole = () => {
      const mole = moleRef.current;
      const hammer = hammerRef.current;
      if (!mole || !hammer || tryResolved) return;
      tryResolved = true;

      currentRound += 1;
      if (onCountChangeRef.current) onCountChangeRef.current(currentRound, totalRounds);
      console.log(`[MoleGame] ✅ 성공 ${currentRound}/${totalRounds}`);

      const createHitEffect = (moleObj, scale = 1) => {
        console.log(`[이펙트] 두더지 로컬 위치: [${moleObj.position.x.toFixed(2)}, ${moleObj.position.y.toFixed(2)}, ${moleObj.position.z.toFixed(2)}]`);
        
        const particleCount = 8;
        const particles = [];
        const size = 20 * scale;
        const geometry = new THREE.SphereGeometry(size, 10, 10);
        const material = new THREE.MeshBasicMaterial({
          color: 0xffd700,
          transparent: true,
          opacity: 0.9,
          blending: THREE.AdditiveBlending,
        });

        // ✅ 두더지의 부모 또는 씬
        const parentObj = moleObj.parent || scene;

        for (let i = 0; i < particleCount; i += 1) {
          const p = new THREE.Mesh(geometry, material);
          
          // ✅ 두더지와 같은 좌표계 사용!
          p.position.set(
            moleObj.position.x,
            moleObj.position.y + 100 * scale,  // 머리 위
            moleObj.position.z
          );
          
          if (i === 0) {
            console.log(`[이펙트] 파티클 0 위치: [${p.position.x.toFixed(2)}, ${p.position.y.toFixed(2)}, ${p.position.z.toFixed(2)}]`);
          }
          
          p.frustumCulled = false;
          p.renderOrder = 10;
          p.userData.velocity = new THREE.Vector3(
            (Math.random() - 0.5) * 50 * scale,
            (Math.random() * 50 + 20) * scale,
            (Math.random() - 0.5) * 50 * scale
          );
          
          // ✅ 두더지와 같은 부모에 추가!
          parentObj.add(p);
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
            // ✅ 각 파티클을 그 부모에서 제거
            particles.forEach((p) => {
              if (p.parent) {
                p.parent.remove(p);
              }
            });
          }
        };

        animateParticles();
      };

      // ✅ 1. 망치 떨어지기
      hammer.visible = true;
      const hStartTime = performance.now();
      
      const animateHammer = (now) => {
        const elapsed = now - hStartTime;
        const progress = Math.min(1, elapsed / 250);
        hammer.position.y = THREE.MathUtils.lerp(hammer.userData.hiddenY, hammer.userData.hitY, progress * progress);

        if (progress < 1) {
          requestAnimationFrame(animateHammer);
        } else {
          console.log(`[MoleGame] 💥 망치 충돌!`);
          
          // ✅ 두더지 스케일
          const worldScale = new THREE.Vector3();
          mole.getWorldScale(worldScale);
          const effectScale = Math.max(worldScale.x, worldScale.y, worldScale.z) || 1;
          
          // ✅ 두더지 객체 전달!
          createHitEffect(mole, effectScale);
          
          // ✅ 2. 두더지 내려가기 (망치 맞은 후!)
          const mStartTime = performance.now();
          const startY = mole.position.y;
          const targetY = mole.userData.hiddenY;

          const animateMoleDown = (mNow) => {
            const mElapsed = mNow - mStartTime;
            const mProgress = Math.min(1, mElapsed / 300);
            mole.position.y = THREE.MathUtils.lerp(startY, targetY, mProgress);
            
            if (mProgress < 1) {
              requestAnimationFrame(animateMoleDown);
            } else {
              console.log(`[MoleGame] 📉 두더지 내려감 완료`);
            }
          };
          requestAnimationFrame(animateMoleDown);
        }
      };
      requestAnimationFrame(animateHammer);

      // ✅ 3. 1.5초 후 다음 라운드 (두더지 다시 올리기)
      setTimeout(() => {
        if (hammerRef.current) {
          hammerRef.current.visible = false;
          hammerRef.current.position.y = hammerRef.current.userData.hiddenY;
        }
        
        // ✅ 두더지 다시 올리기!
        if (moleRef.current) {
          moleRef.current.position.y = moleRef.current.userData.originalY;
          console.log(`[MoleGame] 🐹 두더지 다시 올라옴`);
        }
        
        if (currentRound >= totalRounds) {
          gameStateRef.current = "completed";
          setGameState("completed");
        } else {
          beginTry();
        }
      }, 1500);
    };

    const onKeyDown = (e) => { 
      if (e.code === "KeyW" && !holding && gameStateRef.current === "playing") { 
        holding = true; holdStart = performance.now(); 
      } 
    };
    const onKeyUp = (e) => { if (e.code === "KeyW") { holding = false; holdStart = 0; } };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    let rafId;
    const animate = () => {
      rafId = requestAnimationFrame(animate);
      const dt = 0.016;

      if (gameStateRef.current === "playing" && moleRef.current) {
        if (phase === "show") {
          showTimer += dt;
          const isFirstTry = currentRound === 0;
          const maxShowDuration = isFirstTry ? firstShowDuration : baseShowDuration;
          
          // ✅ 시간 초과 실패
          if (showTimer >= maxShowDuration && !hitTriggered && !tryResolved) { 
            hitTriggered = true;
            tryResolved = true;
            console.log(`[MoleGame] ❌ 시간 초과`);
            
            const startY = moleRef.current.position.y;
            const targetY = moleRef.current.userData.hiddenY;
            const mStartTime = performance.now();
            
            const failAnim = (mNow) => {
              const mp = Math.min(1, (mNow - mStartTime) / 400);
              moleRef.current.position.y = THREE.MathUtils.lerp(startY, targetY, mp);
              
              if (mp < 1) {
                requestAnimationFrame(failAnim);
              } else {
                // 두더지 다시 올리기
                setTimeout(() => {
                  if (moleRef.current) {
                    moleRef.current.position.y = moleRef.current.userData.originalY;
                  }
                  
                  currentRound += 1;
                  if (onCountChangeRef.current) onCountChangeRef.current(currentRound, totalRounds);
                  
                  if (currentRound >= totalRounds) {
                    gameStateRef.current = "completed";
                    setGameState("completed");
                  } else {
                    beginTry();
                  }
                }, 500);
              }
            };
            requestAnimationFrame(failAnim);
          }
          
          // ✅ W 키 성공
          if (holding && !hitTriggered && !tryResolved && (performance.now() - holdStart >= 1000)) { 
            hitTriggered = true; 
            hitMole(); 
          }
          
          // ✅ 센서 성공
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