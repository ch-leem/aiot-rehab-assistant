import socket
import json
import time
import threading
import collections
from dataclasses import dataclass
from typing import Optional, Deque, Tuple


# IMU sample 데이터 구조
@dataclass
class ImuSample:
    host_ts_ms: float
    imu_ts_ms: int
    strength_cmps: float
    seq: int


class ImuUdpBuffer:
    '''
    UDP 소켓 관리
    백그라운드 수신 스레드 관리
    시간 기준 버퍼 유지
    카메라 프레임 기준 IMU 매칭
    '''

    def __init__(self, listen_ip: str = "0.0.0.0", listen_port: int = 9999, max_age_sec: float = 8.0):
        self.listen_ip = listen_ip
        self.listen_port = int(listen_port)
        self.max_age_ms = float(max_age_sec) * 1000.0

        self.buf: Deque[ImuSample] = collections.deque()
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
                    strength = float(msg.get("strength", float("nan")))

                    # ts or board_ts
                    ts = int(msg.get("ts", -1))

                    seq = int(msg.get("seq", -1))
                    s = ImuSample(host_ts_ms=now_ms, imu_ts_ms=ts, strength_cmps=strength, seq=seq)
                    with self._lock:
                        self.buf.append(s)
                except Exception:
                    pass

            with self._lock:
                while self.buf and (now_ms - self.buf[0].host_ts_ms) > self.max_age_ms:
                    self.buf.popleft()

            time.sleep(0.001)

    def match_nearest(self, target_host_ts_ms: float) -> Tuple[Optional[ImuSample], float]:
        """Return closest sample and age_ms = target - sample.host_ts_ms."""
        '''
        가장 가까운 IMU 샘플을 찾아 반환
        '''
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

    def match_interp(self, target_host_ts_ms: float) -> Tuple[Optional[ImuSample], float, bool]:
        """Linear interpolation of strength by host_ts_ms. Returns (sample_like, age_ms, used_interp)."""
        '''
        선형 보간법을 사용하여 주어진 타겟 타임스탬프에 맞는 IMU 샘플을 반환
        '''
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

            strength = (1.0 - w) * prev.strength_cmps + w * nxt.strength_cmps
            imu_ts = -1
            if prev.imu_ts_ms >= 0 and nxt.imu_ts_ms >= 0:
                imu_ts = int(round((1.0 - w) * prev.imu_ts_ms + w * nxt.imu_ts_ms))

            seq = prev.seq if abs(target_host_ts_ms - t0) <= abs(t1 - target_host_ts_ms) else nxt.seq

            samp = ImuSample(host_ts_ms=target_host_ts_ms, imu_ts_ms=imu_ts, strength_cmps=float(strength), seq=int(seq))
            return samp, 0.0, True
