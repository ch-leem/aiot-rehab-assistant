import { useEffect, useRef } from "react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

export default function ArmRaiseGame() {
  const containerRef = useRef(null);
  const barRef = useRef(null);
  const stateRef = useRef(null);
  const countRef = useRef(null);
  const msgRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment()).texture;
    scene.background = new THREE.Color(0xf2f5fa);
    scene.fog = new THREE.Fog(0xf2f5fa, 5, 30);

    const camera = new THREE.PerspectiveCamera(
      55,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    );
    camera.position.set(0, 1.75, 3.1);
    camera.lookAt(0, 1.9, -4);

    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.position.set(6, 10, 4);
    sun.castShadow = true;
    scene.add(sun);
    scene.add(new THREE.AmbientLight(0xffffff, 0.55));

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(40, 40),
      new THREE.MeshStandardMaterial({ color: 0xd8c9b4, roughness: 0.95 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    const table = new THREE.Mesh(
      new THREE.BoxGeometry(3.2, 0.15, 1.4),
      new THREE.MeshStandardMaterial({ color: 0x4a4f58, roughness: 0.8 })
    );
    table.position.set(0, 1, 0.2);
    table.castShadow = true;
    scene.add(table);

    function makeRack() {
      const g = new THREE.Group();
      const metal = new THREE.MeshStandardMaterial({
        color: 0xd4dae3,
        metalness: 0.92,
        roughness: 0.28,
      });
      const plastic = new THREE.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.6 });

      const baseZ = -3.9;
      const topY = 2.95;
      const footY = 0.06;
      const halfW = 1.35;
      const halfD = 0.55;
      const legOut = 1.18;

      const addTube = (a, b, r, mat) => {
        const dir = new THREE.Vector3().subVectors(b, a);
        const len = dir.length();
        const geo = new THREE.CylinderGeometry(r, r, len, 28);
        const m = new THREE.Mesh(geo, mat);
        m.position.copy(a).add(b).multiplyScalar(0.5);
        m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
        m.castShadow = true;
        return m;
      };

      const topFL = new THREE.Vector3(-halfW, topY, baseZ - halfD);
      const topFR = new THREE.Vector3(halfW, topY, baseZ - halfD);
      const topBL = new THREE.Vector3(-halfW, topY, baseZ + halfD);
      const topBR = new THREE.Vector3(halfW, topY, baseZ + halfD);

      const footFL = new THREE.Vector3(-halfW * legOut, footY, baseZ - halfD * legOut);
      const footFR = new THREE.Vector3(halfW * legOut, footY, baseZ - halfD * legOut);
      const footBL = new THREE.Vector3(-halfW * legOut, footY, baseZ + halfD * legOut);
      const footBR = new THREE.Vector3(halfW * legOut, footY, baseZ + halfD * legOut);

      g.add(addTube(footFL, topFL, 0.035, metal));
      g.add(addTube(footFR, topFR, 0.035, metal));
      g.add(addTube(footBL, topBL, 0.035, metal));
      g.add(addTube(footBR, topBR, 0.035, metal));

      g.add(addTube(topFL, topFR, 0.03, metal));
      g.add(addTube(topBL, topBR, 0.03, metal));
      g.add(addTube(topFL, topBL, 0.03, metal));
      g.add(addTube(topFR, topBR, 0.03, metal));

      const midY = 1.1;
      const midFL = new THREE.Vector3(-halfW * 0.9, midY, baseZ - halfD * 0.9);
      const midFR = new THREE.Vector3(halfW * 0.9, midY, baseZ - halfD * 0.9);
      const midBL = new THREE.Vector3(-halfW * 0.9, midY, baseZ + halfD * 0.9);
      const midBR = new THREE.Vector3(halfW * 0.9, midY, baseZ + halfD * 0.9);

      g.add(addTube(midFL, midFR, 0.028, metal));
      g.add(addTube(midBL, midBR, 0.028, metal));
      g.add(addTube(midFL, midBL, 0.028, metal));
      g.add(addTube(midFR, midBR, 0.028, metal));

      const barCount = 6;
      for (let i = 0; i < barCount; i += 1) {
        const t = i / (barCount - 1);
        const z = THREE.MathUtils.lerp(baseZ - halfD * 0.75, baseZ + halfD * 0.75, t);
        const a = new THREE.Vector3(-halfW * 0.92, topY - 0.03, z);
        const b = new THREE.Vector3(halfW * 0.92, topY - 0.03, z);
        g.add(addTube(a, b, 0.022, metal));
      }

      const jointGeo = new THREE.SphereGeometry(0.04, 20, 16);
      for (const p of [topFL, topFR, topBL, topBR]) {
        const j = new THREE.Mesh(jointGeo, metal);
        j.position.copy(p);
        j.castShadow = true;
        g.add(j);
      }

      const footGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.05, 16);
      for (const p of [footFL, footFR, footBL, footBR]) {
        const f = new THREE.Mesh(footGeo, plastic);
        f.position.copy(p);
        f.rotation.x = Math.PI / 2;
        f.castShadow = true;
        g.add(f);
      }

      scene.add(g);
      const xs = [-1.08, -0.36, 0.36, 1.08];
      return xs.map((x) => new THREE.Vector3(x, topY - 0.05, baseZ));
    }

    const hangPoints = makeRack();

    class Cloth {
      constructor(color) {
        this.geo = new THREE.PlaneGeometry(0.9, 0.65, 22, 16);
        this.geo.rotateY(Math.PI);
        this.mat = new THREE.MeshStandardMaterial({
          color,
          roughness: 0.95,
          side: THREE.DoubleSide,
        });
        this.mesh = new THREE.Mesh(this.geo, this.mat);
        this.mesh.castShadow = true;
        scene.add(this.mesh);

        this.p = [];
        this.pp = [];
        this.pin = [];

        const pos = this.geo.attributes.position;
        for (let i = 0; i < pos.count; i += 1) {
          const v = new THREE.Vector3(pos.getX(i), pos.getY(i), pos.getZ(i));
          this.p.push(v.clone());
          this.pp.push(v.clone());
          this.pin.push(false);
        }

        this.links = [];
        const w = 22;
        const h = 16;
        const idx = (x, y) => x + (w + 1) * y;
        const rx = 0.9 / w;
        const ry = 0.65 / h;

        for (let y = 0; y <= h; y += 1) {
          for (let x = 0; x <= w; x += 1) {
            if (x < w) this.links.push([idx(x, y), idx(x + 1, y), rx]);
            if (y < h) this.links.push([idx(x, y), idx(x, y + 1), ry]);
          }
        }

        this.enabled = false;
        this.gravity = -14.5;
        this.damping = 0.972;
        this.w = w;
        this.h = h;
      }

      pinTop() {
        const idx = (x, y) => x + (this.w + 1) * y;
        this.pin[idx(0, this.h)] = true;
        this.pin[idx(this.w, this.h)] = true;
      }

      setPinPos(l, r) {
        const idx = (x, y) => x + (this.w + 1) * y;
        this.p[idx(0, this.h)].copy(l);
        this.p[idx(this.w, this.h)].copy(r);
        this.pp[idx(0, this.h)].copy(l);
        this.pp[idx(this.w, this.h)].copy(r);
      }

      step(dt) {
        if (!this.enabled) return;
        const pos = this.geo.attributes.position;

        for (let i = 0; i < this.p.length; i += 1) {
          if (this.pin[i]) continue;
          const cur = this.p[i];
          const prev = this.pp[i];
          const vel = cur.clone().sub(prev).multiplyScalar(this.damping);
          const next = cur.clone().add(vel);
          next.y += this.gravity * dt * dt;
          this.pp[i] = cur.clone();
          this.p[i] = next;
        }

        for (let k = 0; k < 4; k += 1) {
          for (const [a, b, r] of this.links) {
            const p1 = this.p[a];
            const p2 = this.p[b];
            const d = p2.clone().sub(p1);
            const dist = d.length() || 0.0001;
            const diff = (dist - r) / dist * 0.5;
            if (!this.pin[a]) p1.add(d.clone().multiplyScalar(diff));
            if (!this.pin[b]) p2.sub(d.clone().multiplyScalar(diff));
          }
        }

        for (let i = 0; i < this.p.length; i += 1) {
          pos.setXYZ(i, this.p[i].x, this.p[i].y, this.p[i].z);
        }

        pos.needsUpdate = true;
        this.geo.computeVertexNormals();
      }
    }

    const colors = [0x5fa8ff, 0xff7a7a, 0x7cff9d, 0xffd66b];
    const clothes = [];
    const startX = [-1.1, -0.37, 0.37, 1.1];

    for (let i = 0; i < 4; i += 1) {
      const c = new Cloth(colors[i]);
      c.mesh.position.set(startX[i], 1.15, 0.35);
      c.mesh.rotation.x = -0.2;
      clothes.push(c);
    }

    let active = 0;
    let hold = false;
    let progress = 0;
    const total = clothes.length;

    const hang = (cloth, pt) => {
      cloth.mesh.position.copy(pt);
      cloth.mesh.rotation.set(0, Math.PI, 0);
      cloth.enabled = true;
      cloth.pinTop();

      const left = pt.clone().add(new THREE.Vector3(-0.18, 0, 0));
      const right = pt.clone().add(new THREE.Vector3(0.18, 0, 0));
      const inv = cloth.mesh.matrixWorld.clone().invert();
      cloth.setPinPos(left.applyMatrix4(inv), right.applyMatrix4(inv));
    };

    let audioCtx = null;
    let masterGain = null;

    const ensureAudio = () => {
      if (audioCtx) return;
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      masterGain = audioCtx.createGain();
      masterGain.gain.value = 0.18;
      masterGain.connect(audioCtx.destination);
    };

    const playHangSfx = () => {
      if (!audioCtx || audioCtx.state !== "running") return;
      const now = audioCtx.currentTime;
      const gain = audioCtx.createGain();
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.28, now + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.14);
      gain.connect(masterGain);

      const osc1 = audioCtx.createOscillator();
      osc1.type = "square";
      osc1.frequency.setValueAtTime(720, now);
      osc1.frequency.exponentialRampToValueAtTime(260, now + 0.12);
      osc1.connect(gain);

      const osc2 = audioCtx.createOscillator();
      osc2.type = "triangle";
      osc2.frequency.setValueAtTime(1200, now);
      osc2.frequency.exponentialRampToValueAtTime(340, now + 0.1);
      osc2.connect(gain);

      const noiseBuf = audioCtx.createBuffer(
        1,
        Math.floor(audioCtx.sampleRate * 0.08),
        audioCtx.sampleRate
      );
      const data = noiseBuf.getChannelData(0);
      for (let i = 0; i < data.length; i += 1) data[i] = (Math.random() * 2 - 1) * 0.35;
      const noise = audioCtx.createBufferSource();
      noise.buffer = noiseBuf;
      const hp = audioCtx.createBiquadFilter();
      hp.type = "highpass";
      hp.frequency.setValueAtTime(900, now);
      noise.connect(hp);
      hp.connect(gain);

      osc1.start(now);
      osc1.stop(now + 0.14);
      osc2.start(now);
      osc2.stop(now + 0.14);
      noise.start(now);
      noise.stop(now + 0.08);
    };

    const updateHud = () => {
      if (barRef.current) barRef.current.style.width = `${progress * 100}%`;
      if (stateRef.current) {
        stateRef.current.textContent =
          active >= total ? "완료" : hold || progress > 0 ? "진행" : "대기";
      }
      if (countRef.current) countRef.current.textContent = String(active);
      if (msgRef.current) {
        msgRef.current.textContent =
          active >= total
            ? "완료! 잘했어요. 다음 단계로 이동하세요."
            : "W를 누르고 유지하세요. 목표 위치에 도달하면 자동으로 걸립니다.";
      }
    };

    const onKeyDown = (e) => {
      if (e.code !== "KeyW") return;
      hold = true;
      ensureAudio();
      if (audioCtx.state !== "running") audioCtx.resume();
    };

    const onKeyUp = (e) => {
      if (e.code !== "KeyW") return;
      hold = false;
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);

    const clock = new THREE.Clock();
    let rafId = 0;

    const animate = () => {
      rafId = requestAnimationFrame(animate);
      const dt = Math.min(0.033, clock.getDelta());

      if (active < clothes.length) {
        const c = clothes[active];
        if (!c.enabled) {
          if (hold) progress = Math.min(1, progress + 0.8 * dt);
          else progress = Math.max(0, progress - 0.3 * dt);

          const e = 1 - Math.pow(1 - progress, 3);
          c.mesh.position.y = 1.15 + e * 1.8;
          c.mesh.position.z = 0.35 - e * 4.1;

          if (progress >= 1) {
            hang(c, hangPoints[active]);
            playHangSfx();
            active += 1;
            progress = 0;
          }
        }
      }

      for (const c of clothes) c.step(dt);
      updateHud();
      renderer.render(scene, camera);
    };

    updateHud();
    animate();

    const resize = () => {
      const w = container.clientWidth || 1;
      const h = container.clientHeight || 1;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      resizeObserver.disconnect();
      cancelAnimationFrame(rafId);
      renderer.dispose();
      scene.clear();
      if (audioCtx && audioCtx.state !== "closed") audioCtx.close();
      if (renderer.domElement.parentElement) {
        renderer.domElement.parentElement.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div className="arm-raise-wrapper">
      <div ref={containerRef} className="arm-raise-container" />
      <div className="arm-raise-hud">
        <div className="arm-raise-title">🧺 재활 게이미피케이션: 티셔츠 빨래 걸기</div>
        <div className="arm-raise-sub">
          시선 고정 · W 유지(팔 올리기) → 목표 높이 도달 시 자동으로 “착!”
        </div>
        <div className="arm-raise-row">
          <div className="arm-raise-pill">조작: <b>W</b> 유지</div>
          <div className="arm-raise-pill">상태: <span ref={stateRef}>대기</span></div>
          <div className="arm-raise-pill">
            성공: <span ref={countRef}>0</span>/4
          </div>
        </div>
        <div className="arm-raise-bar-wrap">
          <div ref={barRef} className="arm-raise-bar" />
        </div>
        <div ref={msgRef} className="arm-raise-msg">
          W를 누르고 유지하세요. 목표 위치에 도달하면 자동으로 걸립니다.
        </div>
      </div>
      <div className="arm-raise-hint">팔을 들어올리듯 <b>W</b>를 눌러 유지</div>
      <div className="arm-raise-footer">🔊 사운드: 첫 키 입력 이후 활성화</div>
    </div>
  );
}
