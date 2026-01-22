from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import redis


def env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    return int(v) if v is not None and v != "" else default


REDIS_HOST = env_str("REDIS_HOST", "redis")
REDIS_PORT = env_int("REDIS_PORT", 6379)
REDIS_DB = env_int("REDIS_DB", 0)
LATEST_TTL_SECONDS = env_int("LATEST_TTL_SECONDS", 0)  # 0이면 TTL 미사용

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

app = FastAPI(title="Rehab IoT Ingest API", version="0.1.0")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def latest_key(device_id: str, joint: str) -> str:
    # 키 규칙: latest:device:{deviceId}:joint:{joint}
    return f"latest:device:{device_id}:joint:{joint}"


class JointVector(BaseModel):
    x: float
    y: float
    z: float


class IngestLatestRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    joint: str = Field(..., min_length=1)  # e.g., "elbow", "knee"
    vec: JointVector
    ts: Optional[str] = None  # optional ISO timestamp from device


@app.get("/health")
def health() -> Dict[str, Any]:
    try:
        pong = r.ping()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis ping failed: {e}")
    return {
        "ok": True,
        "redis": pong,
        "redis_host": REDIS_HOST,
        "redis_port": REDIS_PORT,
        "redis_db": REDIS_DB,
        "ttl_seconds": LATEST_TTL_SECONDS,
    }


@app.post("/ingest/latest")
def ingest_latest(req: IngestLatestRequest) -> Dict[str, Any]:
    ts = req.ts or now_iso()
    key = latest_key(req.device_id, req.joint)

    value = {
        "x": req.vec.x,
        "y": req.vec.y,
        "z": req.vec.z,
        "ts": ts,
    }
    payload = json.dumps(value, ensure_ascii=False)

    try:
        if LATEST_TTL_SECONDS > 0:
            r.set(key, payload, ex=LATEST_TTL_SECONDS)
        else:
            r.set(key, payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis set failed: {e}")

    return {"ok": True, "key": key, "stored": value}


@app.get("/latest")
def get_latest(device_id: str, joint: str) -> Dict[str, Any]:
    key = latest_key(device_id, joint)
    try:
        raw = r.get(key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis get failed: {e}")

    if raw is None:
        raise HTTPException(status_code=404, detail=f"Not found: {key}")

    try:
        data = json.loads(raw)
    except Exception:
        data = raw

    return {"ok": True, "key": key, "data": data}
