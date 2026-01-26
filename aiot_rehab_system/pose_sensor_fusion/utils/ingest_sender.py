import threading
import queue
from typing import Optional, Dict, Any

import requests


class IngestSender:
    """
    REST Ingest API로 payload를 비동기 전송
    - 메인 루프는 push만 호출
    - 내부에서 Queue + worker thread로 POST 수행
    """

    def __init__(
        self,
        url: str,
        max_queue: int = 4,
        timeout_sec: float = 0.2,
        drop_policy: str = "drop_old_keep_latest",
        headers: Optional[Dict[str, str]] = None,
        log_every: int = 0,              # 0이면 성공 로그 안 찍음
        log_fail: bool = True,           # 실패는 기본 찍기
    ):
        self.url = url
        self.timeout_sec = float(timeout_sec)
        self.drop_policy = drop_policy
        self.headers = headers or {}

        self.q: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=max_queue)
        self.stop_evt = threading.Event()
        self.th = threading.Thread(target=self._worker, daemon=True)

        self.sess = requests.Session()

        self.sent_ok = 0
        self.sent_fail = 0
        self.last_err = ""

        self.log_every = int(log_every)
        self.log_fail = bool(log_fail)
        self._print_lock = threading.Lock()

    @property
    def maxsize(self) -> int:
        return int(self.q.maxsize)

    def start(self) -> None:
        self.th.start()

    def stop(self) -> None:
        self.stop_evt.set()
        try:
            self.th.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.sess.close()
        except Exception:
            pass

    def push(self, payload: Dict[str, Any]) -> None:
        """
        큐에 payload 삽입
        drop_policy:
          - drop_new: 큐가 꽉 차면 새 payload 버림
          - drop_old_keep_latest: 가장 오래된 것 1개 버리고 최신을 넣음
        """
        if self.stop_evt.is_set():
            return

        try:
            self.q.put_nowait(payload)
            return
        except queue.Full:
            pass

        if self.drop_policy == "drop_new":
            return

        if self.drop_policy == "drop_old_keep_latest":
            try:
                _ = self.q.get_nowait()
            except Exception:
                pass
            try:
                self.q.put_nowait(payload)
            except Exception:
                pass
            return

        try:
            _ = self.q.get_nowait()
        except Exception:
            pass
        try:
            self.q.put_nowait(payload)
        except Exception:
            pass

    def _worker(self) -> None:
        while not self.stop_evt.is_set():
            try:
                payload = self.q.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                r = self.sess.post(
                    self.url,
                    json=payload,
                    headers=self.headers if self.headers else None,
                    timeout=self.timeout_sec,
                )
                if r.ok:
                    self.sent_ok += 1
                    if self.log_every > 0 and (self.sent_ok % self.log_every) == 0:
                        with self._print_lock:
                            print(f"[INGEST OK] ok={self.sent_ok} fail={self.sent_fail} q={self.q.qsize()}")
                else:
                    self.sent_fail += 1
                    self.last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                    if self.log_fail:
                        with self._print_lock:
                            print(f"[INGEST FAIL] ok={self.sent_ok} fail={self.sent_fail} q={self.q.qsize()} err={self.last_err}")
            except Exception as e:
                self.sent_fail += 1
                self.last_err = str(e)
                if self.log_fail:
                    with self._print_lock:
                        print(f"[INGEST EXC] ok={self.sent_ok} fail={self.sent_fail} q={self.q.qsize()} err={self.last_err}")
