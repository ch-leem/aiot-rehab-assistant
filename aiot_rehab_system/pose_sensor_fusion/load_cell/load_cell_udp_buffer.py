import socket
import json
import time
import threading
import collections
from dataclasses import dataclass
from typing import Optional, Deque, Tuple


@dataclass
class WeightSample:
    host_ts_ms: float   # PC가 받은 시간(ms)
    board_ts_ms: int    # 보드가 보낸 ts(ms) (없으면 -1)
    weight_kg: float    # 무게 (kg)
    seq: int            # 시퀀스 (없으면 -1)


class WeightUdpBuffer:
    """
    UDP 소켓 관리
    백그라운드 수신 스레드
    시간 기준 버퍼 유지
    프레임 타임스탬프 기준 가장 가까운 샘플/보간 매칭
    """

    def __init__(self, listen_ip: str = "0.0.0.0", listen_port: int = 9998, max_age_sec: float = 8.0):
        self.listen_ip = listen_ip
        self.listen_port = int(listen_port)
        self.max_age_ms = float(max_age_sec) * 1000.0

        self.buf: Deque[WeightSample] = collections.deque()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._th = None
        self._sock = None

    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((self.listen_ip, self.listen_port))
        self._sock.setblocking(False)
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def stop(self):
        self._stop.set()
        if self._th:
            self._th.join(timeout=0.5)
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    def _run(self):
        while not self._stop.is_set():
            now_ms = time.time() * 1000.0

            while True:
                try:
                    data, _addr = self._sock.recvfrom(2048)
                except BlockingIOError:
                    break

                try:
                    msg = json.loads(data.decode("utf-8"))

                    # weight payload: accept a few key names for robustness
                    # preferred: "weight_kg"
                    w = msg.get("weight_kg", None)
                    if w is None:
                        w = msg.get("kg", None)
                    if w is None:
                        w = msg.get("weight", None)  # fallback

                    weight_kg = float(w) if w is not None else float("nan")

                    ts = int(msg.get("ts", -1))          # board timestamp (ms)
                    seq = int(msg.get("seq", -1))

                    s = WeightSample(
                        host_ts_ms=now_ms,
                        board_ts_ms=ts,
                        weight_kg=weight_kg,
                        seq=seq,
                    )

                    with self._lock:
                        self.buf.append(s)

                except Exception:
                    pass

            # drop old
            with self._lock:
                while self.buf and (now_ms - self.buf[0].host_ts_ms) > self.max_age_ms:
                    self.buf.popleft()

            time.sleep(0.001)

    def match_nearest(self, target_host_ts_ms: float) -> Tuple[Optional[WeightSample], float]:
        """Return closest sample and age_ms = target - sample.host_ts_ms."""
        with self._lock:
            if not self.buf:
                return None, float("inf")

            best = None
            best_abs = 1e18
            for s in self.buf:
                d = target_host_ts_ms - s.host_ts_ms
                ad = abs(d)
                if ad < best_abs:
                    best_abs = ad
                    best = s

            return best, target_host_ts_ms - best.host_ts_ms

    def match_interp(self, target_host_ts_ms: float) -> Tuple[Optional[WeightSample], float, bool]:
        """
        Linear interpolation of weight by host_ts_ms.
        Returns (sample_like, age_ms, used_interp).
        """
        with self._lock:
            if len(self.buf) < 2:
                s, age = self.match_nearest(target_host_ts_ms)
                return s, age, False

            prev = None
            nxt = None
            for s in self.buf:
                if s.host_ts_ms <= target_host_ts_ms:
                    prev = s
                if s.host_ts_ms >= target_host_ts_ms:
                    nxt = s
                    break

            if prev is None or nxt is None or prev.host_ts_ms == nxt.host_ts_ms:
                s, age = self.match_nearest(target_host_ts_ms)
                return s, age, False

            t0, t1 = prev.host_ts_ms, nxt.host_ts_ms
            w = (target_host_ts_ms - t0) / (t1 - t0)

            weight_kg = (1.0 - w) * prev.weight_kg + w * nxt.weight_kg

            board_ts = -1
            if prev.board_ts_ms >= 0 and nxt.board_ts_ms >= 0:
                board_ts = int(round((1.0 - w) * prev.board_ts_ms + w * nxt.board_ts_ms))

            seq = prev.seq if abs(target_host_ts_ms - t0) <= abs(t1 - target_host_ts_ms) else nxt.seq

            samp = WeightSample(
                host_ts_ms=target_host_ts_ms,
                board_ts_ms=board_ts,
                weight_kg=float(weight_kg),
                seq=int(seq),
            )
            return samp, 0.0, True