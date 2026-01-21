#!/usr/bin/env python3
import os
import time
import json
import asyncio
import yaml
from typing import Optional

import websockets


async def recv_loop(ws: websockets.WebSocketClientProtocol) -> None:
    while True:
        msg = await ws.recv()
        # 서버 메시지 수신, 필요하면 여기서 분기 처리
        try:
            obj = json.loads(msg)
        except Exception:
            obj = {"raw": msg}
        print(f"[WS RECV] {obj}")


async def send_heartbeat_loop(
    ws: websockets.WebSocketClientProtocol,
    interval_sec: float,
) -> None:
    while True:
        payload = {"type": "heartbeat", "ts": int(time.time())}
        await ws.send(json.dumps(payload))
        await asyncio.sleep(interval_sec)


async def connect_and_run(
    ws_url: str,
    heartbeat_interval_sec: float = 3.0,
) -> None:
    async with websockets.connect(
        ws_url,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=5,
        max_size=2**20,
    ) as ws:
        print(f"[WS] connected: {ws_url}")

        # 1, 반드시 최초 hello
        await ws.send(json.dumps({"type": "jetson_hello"}))
        print("[WS] sent jetson_hello")

        # 2, 수신 루프 + heartbeat 루프 동시 실행
        recv_task = asyncio.create_task(recv_loop(ws))
        hb_task = asyncio.create_task(send_heartbeat_loop(ws, heartbeat_interval_sec))

        done, pending = await asyncio.wait(
            {recv_task, hb_task},
            return_when=asyncio.FIRST_EXCEPTION,
        )

        # 예외나 종료 발생 시 정리
        for t in pending:
            t.cancel()
        for t in done:
            _ = t.exception() if t.cancelled() is False else None


async def main() -> None:

    with open("/home/a203/workspace/S14P11A203/aiot_rehab_system/configs/pose_sensor_fusion/run.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    ws_url = cfg["ingest"]["url"]
    heartbeat_interval_sec = float(os.getenv("HEARTBEAT_SEC", "3.0"))  # 2~5 권장
    retry_min_sec = float(os.getenv("RETRY_MIN_SEC", "0.5"))
    retry_max_sec = float(os.getenv("RETRY_MAX_SEC", "5.0"))

    backoff = retry_min_sec

    while True:
        try:
            await connect_and_run(ws_url, heartbeat_interval_sec)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[WS] disconnected, err={e}, retry in {backoff:.1f}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 1.5, retry_max_sec)
            continue

        # 정상적으로 connect_and_run이 끝나는 경우도 재연결로 이어가게 처리
        print(f"[WS] session ended, retry in {backoff:.1f}s")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 1.5, retry_max_sec)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
