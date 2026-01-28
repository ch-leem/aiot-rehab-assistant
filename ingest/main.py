from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import redis

# ----------------------------
# Config
# ----------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")  # optional

STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "ingest:stream")   # 단일 스트림
LATEST_KEY = os.getenv("REDIS_LATEST_KEY", "ingest:latest")   # 최신 1개

MAXLEN = int(os.getenv("REDIS_STREAM_MAXLEN", "5000"))        # 최근 N개만 유지(원하면 늘리기)

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,  # 문자열로 저장/조회
)

app = FastAPI(title="Ingest API", version="1.0")


# ----------------------------
# Payload (유연하게 받기)
# ----------------------------
class IngestPayload(BaseModel):
    frames: list[Dict[str, Any]] = Field(default_factory=list)


@app.get("/health")
def health():
    try:
        r.ping()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/stream")
async def ingest_stream(payload: IngestPayload, request: Request):
    """
    patient_id 없이 단일 Stream에 계속 적재
    - Stream: XADD ingest:stream
    - Latest: SET ingest:latest (최신 payload)
    """
    if not payload.frames:
        raise HTTPException(status_code=400, detail="frames is empty")

    now_ms = int(time.time() * 1000)

    # 원본 JSON 그대로 저장(가장 편함)
    payload_json = payload.model_dump_json()

    # (선택) 누가 보냈는지 정도만 메타로 남김
    client_ip = request.client.host if request.client else ""

    event = {
        "ts_ms": str(now_ms),
        "client_ip": client_ip,
        "payload": payload_json,
    }

    try:
        msg_id = r.xadd(STREAM_KEY, event, maxlen=MAXLEN, approximate=True)
        r.set(LATEST_KEY, payload_json)
        return {"ok": True, "stream": STREAM_KEY, "id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"redis error: {e}")
