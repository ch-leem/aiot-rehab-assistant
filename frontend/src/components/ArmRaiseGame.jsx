import { useEffect, useRef } from "react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export default function ArmRaiseGame({ onCountChange }) {
  const containerRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);

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
    scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment()).texture;
    scene.background = new THREE.Color(0xf2f5fa);
    scene.fog = null;

    const camera = new THREE.PerspectiveCamera(58, initW / initH, 0.1, 120);
    camera.position.set(-0.044532207971679935, 1.7996827340612096, 4.74469444693795);
    camera.lookAt(0, 0.75, 0);
    cameraRef.current = camera;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false; // 팬 비활성화
    controls.enableRotate = false; // 회전 비활성화
    controls.enableZoom = false; // 줌 비활성화
    controls.minDistance = 0.8;
    controls.maxDistance = 12;
    controls.target.set(0, 0.75, 0);
    controls.update();
    controlsRef.current = controls;

    const useFixedCamera = true;

    const sun = new THREE.DirectionalLight(0xffffff, 2.0);
    sun.position.set(6, 10, 4);
    sun.castShadow = true;
    scene.add(sun);
    scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    scene.add(new THREE.HemisphereLight(0xffffff, 0xd9cbb8, 0.35));

    const debugBox = new THREE.Mesh(
      new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshStandardMaterial({ color: 0xff6b6b })
    );
    debugBox.visible = false;
    debugBox.position.set(0, 1, 0);
    scene.add(debugBox);

    let hangPoints = [
      new THREE.Vector3(-1.8, 2.9, -3.9),
      new THREE.Vector3(-1.4, 2.9, -3.9),
      new THREE.Vector3(-1.0, 2.9, -3.9),
      new THREE.Vector3(-0.6, 2.9, -3.9),
      new THREE.Vector3(-0.2, 2.9, -3.9),
      new THREE.Vector3(0.2, 2.9, -3.9),
      new THREE.Vector3(0.6, 2.9, -3.9),
      new THREE.Vector3(1.0, 2.9, -3.9),
      new THREE.Vector3(1.4, 2.9, -3.9),
      new THREE.Vector3(1.8, 2.9, -3.9),
    ];

    let startZ = 0.6;
    let baseY = 1.05;
    let stackOrigin = new THREE.Vector3(-1.6, baseY, startZ);
    
    // 더 큰 빨래 바구니 생성
    const basketGroup = new THREE.Group();
    const basketMat = new THREE.MeshStandardMaterial({
      color: 0xd4a574,
      roughness: 0.8,
    });
    
    // 바구니 크기 증가
    const basketWidth = 0.8;
    const basketHeight = 0.35;
    const basketDepth = 0.6;
    const wallThickness = 0.03;
    
    // 바구니 바닥 (두껍게)
    const basketBottom = new THREE.Mesh(
      new THREE.BoxGeometry(basketWidth, 0.08, basketDepth),
      basketMat
    );
    basketBottom.position.set(0, 0.04, 0); // 바닥을 y=0 위치에
    basketBottom.castShadow = true;
    basketBottom.receiveShadow = true;
    
    // 바구니 앞면
    const basketFront = new THREE.Mesh(
      new THREE.BoxGeometry(basketWidth, basketHeight, wallThickness),
      basketMat
    );
    basketFront.position.set(0, basketHeight / 2 + 0.08, basketDepth / 2);
    basketFront.castShadow = true;
    basketFront.receiveShadow = true;
    
    // 바구니 뒷면
    const basketBack = new THREE.Mesh(
      new THREE.BoxGeometry(basketWidth, basketHeight, wallThickness),
      basketMat
    );
    basketBack.position.set(0, basketHeight / 2 + 0.08, -basketDepth / 2);
    basketBack.castShadow = true;
    basketBack.receiveShadow = true;
    
    // 바구니 왼쪽면
    const basketLeft = new THREE.Mesh(
      new THREE.BoxGeometry(wallThickness, basketHeight, basketDepth),
      basketMat
    );
    basketLeft.position.set(-basketWidth / 2, basketHeight / 2 + 0.08, 0);
    basketLeft.castShadow = true;
    basketLeft.receiveShadow = true;
    
    // 바구니 오른쪽면
    const basketRight = new THREE.Mesh(
      new THREE.BoxGeometry(wallThickness, basketHeight, basketDepth),
      basketMat
    );
    basketRight.position.set(basketWidth / 2, basketHeight / 2 + 0.08, 0);
    basketRight.castShadow = true;
    basketRight.receiveShadow = true;
    
    basketGroup.add(basketBottom, basketFront, basketBack, basketLeft, basketRight);
    basketGroup.position.set(stackOrigin.x, baseY, stackOrigin.z);
    scene.add(basketGroup);

    const loader = new GLTFLoader();
    loader.load(
      "/living_room2.glb",
      (gltf) => {
        const room = gltf.scene;
        if (!room) {
          debugBox.visible = true;
          return;
        }

        room.traverse((obj) => {
          if (obj.isMesh) {
            obj.castShadow = true;
            obj.receiveShadow = true;
          }
        });
        room.position.set(0, 0, 0);
        room.scale.set(1, 1, 1);
        room.rotation.y = Math.PI;
        scene.add(room);

        let bounds = new THREE.Box3().setFromObject(room);
        const size = bounds.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        if (maxDim > 50) {
          const scale = 10 / maxDim;
          room.scale.setScalar(scale);
          bounds = new THREE.Box3().setFromObject(room);
        }

        const resizedSize = bounds.getSize(new THREE.Vector3());
        const floorY = bounds.min.y;

        if (!useFixedCamera) {
          const resizedCenter = bounds.getCenter(new THREE.Vector3());
          const fov = camera.fov * (Math.PI / 180);
          let cameraZ = Math.abs(
            Math.max(resizedSize.x, resizedSize.y, resizedSize.z) / (2 * Math.tan(fov / 2))
          );
          cameraZ *= 0.72;
          camera.position.set(
            resizedCenter.x,
            floorY + resizedSize.y * 0.45,
            resizedCenter.z + cameraZ
          );
          camera.lookAt(resizedCenter.x, floorY + resizedSize.y * 0.25, resizedCenter.z);
          controls.target.set(resizedCenter.x, floorY + resizedSize.y * 0.25, resizedCenter.z);
          controls.update();
        }

        startZ = bounds.max.z + resizedSize.z * 0.06;
        baseY = floorY + resizedSize.y * 0.12;
        stackOrigin = new THREE.Vector3(
          bounds.min.x + resizedSize.x * 0.18,
          baseY,
          bounds.max.z + resizedSize.z * 0.08
        );
        
        // 바구니 위치 업데이트
        basketGroup.position.set(stackOrigin.x, baseY, stackOrigin.z);

        let rackObject = null;
        room.traverse((obj) => {
          if ((obj.name || "").toLowerCase() === "object_4") rackObject = obj;
        });

        if (rackObject) {
          const box = new THREE.Box3().setFromObject(rackObject);
          const size = new THREE.Vector3();
          const center = new THREE.Vector3();
          box.getSize(size);
          box.getCenter(center);

          const width = size.x || 1.2;
          const baseTopY = box.max.y - 0.15;
          const z = center.z + size.z * 0.15;
          const span = width * 0.48;

          hangPoints = [];
          for (let i = 0; i < 10; i++) {
            const t = i / 9;
            const x = center.x - span + t * span * 2;
            
            // 높이 변화: 2~3번은 낮아지고, 4~7번은 6번 높이로 평평, 8~9번은 올라감
            let yOffset = 0;
            if (i >= 1 && i <= 2) {
              // 2~3번 (index 1~2): 점점 낮아짐
              const dropAmount = (i - 0) * 0.08; // 각 옷마다 8cm씩 낮아짐
              yOffset = -dropAmount;
            } else if (i >= 3 && i <= 6) {
              // 4~7번 (index 3~6): 6번 높이로 평평하게
              yOffset = -0.24; // 3번이 내려간 높이 유지
            } else if (i >= 7 && i <= 8) {
              // 8~9번 (index 7~8): 점점 올라감
              const riseAmount = (i - 6) * 0.08; // 7번부터 다시 올라감
              yOffset = -0.24 + riseAmount;
            }
            
            hangPoints.push(new THREE.Vector3(x, baseTopY + yOffset, z));
          }

          const stackOffsetX = width * 0.7;
          const stackOffsetZ = size.z * 0.45;
          stackOrigin = new THREE.Vector3(
            center.x - span - stackOffsetX,
            baseY + 0.02,
            z + stackOffsetZ
          );
        }

        basketGroup.position.set(stackOrigin.x, baseY, stackOrigin.z);

        clothes.forEach((c, i) => {
          if (!c.started) {
            const randomRotY = (Math.random() - 0.5) * 0.4;
            const randomRotX = -0.2 + (Math.random() - 0.5) * 0.15;
            const randomOffsetX = (Math.random() - 0.5) * 0.2;
            const randomOffsetZ = (Math.random() - 0.5) * 0.15;
            
            c.mesh.position.set(
              stackOrigin.x + randomOffsetX,
              baseY + 0.15 + i * 0.03, // 바구니 바닥 위에 쌓임
              stackOrigin.z + randomOffsetZ
            );
            c.mesh.rotation.x = randomRotX;
            c.mesh.rotation.y = randomRotY;
            c.mesh.scale.set(0.8, 0.8, 0.8);
          }
        });
      },
      undefined,
      (err) => {
        console.warn("GLB load failed", err);
        debugBox.visible = true;
      }
    );

    class Cloth {
      constructor(color, index, type) {
        this.index = index;
        this.type = type;
        
        this.mesh = new THREE.Group();
        
        const mat = new THREE.MeshStandardMaterial({
          color,
          roughness: 0.95,
          side: THREE.DoubleSide,
        });
        const thickness = 0.04;
        
        if (type === 'shirt') {
          const bodyGeo = new THREE.BoxGeometry(0.35, 0.45, thickness);
          const body = new THREE.Mesh(bodyGeo, mat);
          body.castShadow = true;
          body.receiveShadow = true;
          
          const leftArmGeo = new THREE.BoxGeometry(0.12, 0.25, thickness);
          const leftArm = new THREE.Mesh(leftArmGeo, mat);
          leftArm.position.set(-0.235, 0.08, 0);
          leftArm.rotation.z = -0.3;
          leftArm.castShadow = true;
          
          const rightArmGeo = new THREE.BoxGeometry(0.12, 0.25, thickness);
          const rightArm = new THREE.Mesh(rightArmGeo, mat);
          rightArm.position.set(0.235, 0.08, 0);
          rightArm.rotation.z = 0.3;
          rightArm.castShadow = true;
          
          this.mesh.add(body, leftArm, rightArm);
        } else if (type === 'pants') {
          const waistGeo = new THREE.BoxGeometry(0.35, 0.1, thickness);
          const waist = new THREE.Mesh(waistGeo, mat);
          waist.position.set(0, 0.2, 0);
          waist.castShadow = true;
          
          const leftLegGeo = new THREE.BoxGeometry(0.15, 0.4, thickness);
          const leftLeg = new THREE.Mesh(leftLegGeo, mat);
          leftLeg.position.set(-0.1, -0.05, 0);
          leftLeg.castShadow = true;
          
          const rightLegGeo = new THREE.BoxGeometry(0.15, 0.4, thickness);
          const rightLeg = new THREE.Mesh(rightLegGeo, mat);
          rightLeg.position.set(0.1, -0.05, 0);
          rightLeg.castShadow = true;
          
          this.mesh.add(waist, leftLeg, rightLeg);
        } else if (type === 'towel') {
          const towelGeo = new THREE.BoxGeometry(0.3, 0.4, thickness);
          const towel = new THREE.Mesh(towelGeo, mat);
          towel.castShadow = true;
          towel.receiveShadow = true;
          
          this.mesh.add(towel);
        }
        
        scene.add(this.mesh);

        this.enabled = false;
        this.started = false;
        this.hangSway = 0;
      }

      simulateHanging(dt, hangPoint) {
        if (!this.enabled) return;
        
        const time = Date.now() * 0.001;
        
        const swayDecay = Math.max(0, 1 - this.hangSway * 0.33);
        const swayAmp = 0.25 * swayDecay;
        const swaySpeed = 2.5;
        
        this.mesh.rotation.x = Math.sin(time * swaySpeed) * swayAmp * 0.5;
        this.mesh.rotation.z = Math.cos(time * swaySpeed * 0.7) * swayAmp * 0.8;
        
        this.hangSway += dt;
      }

      flutter(t) {
        if (this.enabled) return;
        
        const amp = 0.01;
        this.mesh.rotation.x = Math.sin(t * 2 + this.index) * amp;
      }
      
      liftAnimation(progress, from, target, t, index) {
        const eased = 1 - Math.pow(1 - progress, 3);
        this.mesh.position.lerpVectors(from, target, eased);
        
        if (progress < 0.6) {
          const wobble = Math.sin(progress * Math.PI * 6 + t * 8) * (1 - progress * 1.5) * 0.02;
          this.mesh.rotation.x = wobble;
          this.mesh.rotation.y = 0;
          this.mesh.scale.set(1, 1, 1);
        } else {
          const rotProgress = (progress - 0.6) / 0.4;
          this.mesh.rotation.y = rotProgress * Math.PI / 2;
          this.mesh.rotation.x = 0;
          this.mesh.scale.set(1, 1, 1);
        }
      }
    }

    const colors = [0x5fa8ff, 0xff7a7a, 0x7cff9d, 0xffd66b, 0xc89dff, 0xff9d9d, 0x9dffc8, 0xffc89d, 0x9dd6ff, 0xffffff];
    const types = ['shirt', 'shirt', 'pants', 'towel', 'shirt', 'pants', 'towel', 'shirt', 'pants', 'towel'];
    const clothes = [];

    for (let i = 0; i < 10; i += 1) {
      const c = new Cloth(colors[i], i, types[i]);
      const randomRotY = (Math.random() - 0.5) * 0.4;
      const randomRotX = -0.2 + (Math.random() - 0.5) * 0.15;
      const randomOffsetX = (Math.random() - 0.5) * 0.2;
      const randomOffsetZ = (Math.random() - 0.5) * 0.15;
      
      c.mesh.position.set(
        stackOrigin.x + randomOffsetX,
        baseY + 0.15 + i * 0.03,
        stackOrigin.z + randomOffsetZ
      );
      c.mesh.rotation.x = randomRotX;
      c.mesh.rotation.y = randomRotY;
      c.mesh.scale.set(0.8, 0.8, 0.8);
      clothes.push(c);
    }

    let active = 0;
    let reps = 0;
    let wasRaised = false;
    let progress = 0;
    const total = clothes.length;

    let audioCtx = null;
    const playHangSfx = () => {
      if (!audioCtx || audioCtx.state !== "running") return;
      const now = audioCtx.currentTime;
      
      const osc1 = audioCtx.createOscillator();
      const osc2 = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      
      osc1.type = "sine";
      osc1.frequency.setValueAtTime(800, now);
      osc1.frequency.exponentialRampToValueAtTime(1200, now + 0.08);
      
      osc2.type = "sine";
      osc2.frequency.setValueAtTime(1600, now);
      osc2.frequency.exponentialRampToValueAtTime(2400, now + 0.08);
      
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.15, now + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.15);
      
      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(audioCtx.destination);
      
      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 0.15);
      osc2.stop(now + 0.15);
    };

    const ensureAudio = () => {
      if (audioCtx) return;
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    };

    const notifyCount = () => {
      if (typeof onCountChange === "function") {
        onCountChange(reps, total);
      }
    };

    const poseSseUrl = import.meta.env.VITE_POSE_SSE_URL || "/api/ingest/events";
    let poseStream = null;
    let targetProgress = 0;
    let lastPoseAt = 0;

    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

    const isValidPoint = (point) =>
      point &&
      typeof point.x === "number" &&
      typeof point.y === "number" &&
      typeof point.conf === "number" &&
      point.conf >= 0.3;

    const flexScore = (flexion) => {
      if (typeof flexion !== "number") return null;
      return clamp((flexion - 30) / 60, 0, 1);
    };

    const limbRaiseScore = (shoulder, wrist, hip) => {
      if (!isValidPoint(shoulder) || !isValidPoint(wrist)) return null;
      const dy = shoulder.y - wrist.y;
      if (dy <= 0) return 0;

      let denom = 0.3;
      if (isValidPoint(hip)) {
        const torso = Math.abs(hip.y - shoulder.y);
        if (torso > 0) denom = torso * 0.8;
      }

      return clamp(dy / denom, 0, 1);
    };

    const getArmRaiseScore = (frame) => {
      if (!frame) return 0;
      const scores = [];
      const deg = frame.deg || {};
      const leftDeg = deg.left || {};
      const rightDeg = deg.right || {};
      const leftFlex = flexScore(leftDeg.shoulder_flexion);
      const rightFlex = flexScore(rightDeg.shoulder_flexion);

      if (typeof leftFlex === "number") scores.push(leftFlex);
      if (typeof rightFlex === "number") scores.push(rightFlex);

      const pos = frame.position || {};
      const left = pos.left || {};
      const right = pos.right || {};

      const leftScore = limbRaiseScore(left.left_shoulder, left.left_wrist, left.left_hip);
      const rightScore = limbRaiseScore(right.right_shoulder, right.right_wrist, right.right_hip);

      if (typeof leftScore === "number") scores.push(leftScore);
      if (typeof rightScore === "number") scores.push(rightScore);

      return scores.length ? Math.max(...scores) : 0;
    };
    console.log("[SSE] condition check", {
      poseSseUrl,
      eventSourceType: typeof EventSource,
    });
    if (poseSseUrl && typeof EventSource !== "undefined") {
      try {
        poseStream = new EventSource(poseSseUrl);
        poseStream.onmessage = (ev) => {
          try {
            console.log("[SSE] pose message", ev.data);
            const payload = JSON.parse(ev.data);
            const frames = Array.isArray(payload?.frames) ? payload.frames : [];
            const frame = frames.length ? frames[frames.length - 1] : null;
            const score = getArmRaiseScore(frame);
            targetProgress = score;
            lastPoseAt = performance.now();
            if (score > 0) {
              ensureAudio();
              if (audioCtx && audioCtx.state !== "running") audioCtx.resume();
            }
          } catch {
            // ignore parse errors
          }
        };
        poseStream.onerror = () => {
          targetProgress = 0;
        };
      } catch {
        // ignore stream errors
      }
    }

    const clock = new THREE.Clock();
    let rafId = 0;

    const animate = () => {
      rafId = requestAnimationFrame(animate);
      const dt = Math.min(0.033, clock.getDelta());
      const t = clock.elapsedTime;

      if (active < clothes.length) {
        const c = clothes[active];
        if (!c.enabled) {
          if (lastPoseAt && performance.now() - lastPoseAt > 500) {
            targetProgress = 0;
          }
          const smoothing = 1 - Math.exp(-dt * 6);
          progress += (targetProgress - progress) * smoothing;
          progress = Math.max(0, Math.min(1, progress));

          const raiseThreshold = 0.6;
          const lowerThreshold = 0.35;
          const signal = targetProgress;

          if (!wasRaised && signal >= raiseThreshold) {
            wasRaised = true;
          }

          if (wasRaised && signal <= lowerThreshold) {
            wasRaised = false;
            if (reps < total) {
              reps += 1;
              notifyCount();
            }
          }

          const target = hangPoints[active];
          const randomOffsetX = (Math.random() - 0.5) * 0.2;
          const randomOffsetZ = (Math.random() - 0.5) * 0.15;
          const from = new THREE.Vector3(
            stackOrigin.x + randomOffsetX,
            baseY + 0.15 + active * 0.03,
            stackOrigin.z + randomOffsetZ
          );
          
          if (progress > 0) {
            c.mesh.scale.lerp(new THREE.Vector3(1, 1, 1), progress * 2);
          }
          
          c.liftAnimation(progress, from, target, t, active);
          c.started = true;

          if (progress >= 1) {
            c.enabled = true;
            c.hangSway = 0;
            c.mesh.rotation.y = Math.PI / 2;
            c.mesh.rotation.x = 0;
            c.mesh.scale.set(1, 1, 1);
            playHangSfx();
            active += 1;
            progress = 0;
          }
        }
      }

      clothes.forEach((c, i) => {
        if (c.enabled) {
          c.simulateHanging(dt, hangPoints[i]);
        } else {
          c.flutter(t);
        }
      });
      
      controls.update();
      renderer.render(scene, camera);
    };

    notifyCount();
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
      if (poseStream) {
        poseStream.close();
        poseStream = null;
      }
      resizeObserver.disconnect();
      cancelAnimationFrame(rafId);
      controls.dispose();
      renderer.dispose();
      scene.clear();
      cameraRef.current = null;
      controlsRef.current = null;
      if (audioCtx && audioCtx.state !== "closed") audioCtx.close();
      if (renderer.domElement.parentElement) {
        renderer.domElement.parentElement.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div className="arm-raise-wrapper">
      <div ref={containerRef} className="arm-raise-container" />
    </div>
  );
}
