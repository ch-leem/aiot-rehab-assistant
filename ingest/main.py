from __future__ import annotations

import os
import time
import math
import logging
from typing import Any, Dict, Optional, Tuple


from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import redis

# ----------------------------
# Config
# ----------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

# 기존(단일)
STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "ingest:stream")
LATEST_KEY = os.getenv("REDIS_LATEST_KEY", "ingest:latest")
MAXLEN = int(os.getenv("REDIS_STREAM_MAXLEN", "5000"))

# ✅ Try 제어
ACTIVE_TRY_KEY = os.getenv("ACTIVE_TRY_KEY", "ingest:active_try")

# ✅ 집계 설정
REDIS_AGG_PREFIX = os.getenv("REDIS_AGG_PREFIX", "agg:try")  # compose: agg:try
# compose 예: strength=sensor.strength,l_ankle_x=position.left.left_ankle.x,...
AGG_METRICS = os.getenv("AGG_METRICS", "strength=sensor.strength,l_ankle_x=position.left.left_ankle.x,l_ankle_y=position.left.left_ankle.y,l_ankle_z=position.left.left_ankle.z,r_ankle_x=position.right.right_ankle.x,r_ankle_y=position.right.right_ankle.y,r_ankle_z=position.right.right_ankle.z,power=sensor.power,trunk_forward_tilt=deg.mid.trunk_forward_tilt,pelvis_level=deg.mid.pelvis_level,l_elbow_extension=deg.left.elbow_extension,r_elbow_extension=deg.right.elbow_extension")

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
)

app = FastAPI(title="Ingest API", version="1.0")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ingest")
# ----------------------------
# Models
# ----------------------------
class IngestPayload(BaseModel):
    frames: list[Dict[str, Any]] = Field(default_factory=list)


class TryStartRequest(BaseModel):
    try_id: str = Field(...)


def _dist3(a, b) -> float:
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)
# ----------------------------
# Utils
# ----------------------------
def _parse_metrics(spec: str) -> Dict[str, str]:
    """
    "strength=sensor.strength,l_ankle_x=position.left.left_ankle.x" -> {"strength":"sensor.strength", ...}
    """
    out: Dict[str, str] = {}
    spec = (spec or "").strip()
    if not spec:
        return out
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    for p in parts:
        if "=" not in p:
            continue
        k, path = p.split("=", 1)
        out[k.strip()] = path.strip()
    return out


METRIC_PATHS = _parse_metrics(AGG_METRICS)


def _get_by_path(obj: Any, path: str) -> Optional[float]:
    """
    path: "sensor.strength" 같은 dot path를 따라가서 숫자(float)로 반환(불가하면 None)
    """
    cur = obj
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    # 숫자로 변환
    try:
        if cur is None:
            return None
        return float(cur)
    except Exception:
        return None


def _agg_key(try_id: str) -> str:
    return f"{REDIS_AGG_PREFIX}:{try_id}"  # 예: agg:try:4


def _try_stream_key(try_id: str) -> str:
    return f"frames:try:{try_id}:stream"


def _try_latest_key(try_id: str) -> str:
    return f"frames:try:{try_id}:latest"


# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health():
    try:
        r.ping()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/try/start")
def try_start(body: TryStartRequest):
    """
    활성 try 설정 + (선택) 집계 초기화
    """
    try_id = (body.try_id or "").strip()
    if not try_id:
        raise HTTPException(status_code=400, detail="try_id is required")

    try:
        r.set(ACTIVE_TRY_KEY, try_id)

        # ✅ 집계 초기화(원하면 주석 해제/유지)
        # 기존 값이 있더라도 새 try 시작 시 초기화하고 싶으면 flush
        r.delete(_agg_key(try_id))

        return {"ok": True, "active_try_key": ACTIVE_TRY_KEY, "try_id": try_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"redis error: {e}")


@app.post("/try/stop")
def try_stop():
    """
    활성 try 해제(이후 ingest는 try 집계/저장 안 함)
    """
    try:
        r.delete(ACTIVE_TRY_KEY)
        return {"ok": True, "active_try_key": ACTIVE_TRY_KEY}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"redis error: {e}")

#값 추가
@app.post("/ingest/stream")
async def ingest_stream(payload: IngestPayload, request: Request):
    """
    프레임 ingest:
    - 단일 Stream/LATEST는 유지
    - ✅ 활성 try가 있으면 try별 Stream/LATEST + 집계 업데이트
    """
    if not payload.frames:
        raise HTTPException(status_code=400, detail="frames is empty")

    now_ms = int(time.time() * 1000)
    payload_json = payload.model_dump_json()
    client_ip = request.client.host if request.client else ""

    # 1) 기존 단일 스트림 적재(원하면 계속 유지)
    event = {"ts_ms": str(now_ms), "client_ip": client_ip, "payload": payload_json}

    try:
        msg_id = r.xadd(STREAM_KEY, event, maxlen=MAXLEN, approximate=True)
        r.set(LATEST_KEY, payload_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"redis error: {e}")

    # 2) ✅ 활성 try가 있으면 try별 처리
    try_id = r.get(ACTIVE_TRY_KEY)
    if try_id:
        # try별 latest/stream 저장
        try_event = {"ts_ms": str(now_ms), "client_ip": client_ip, "payload": payload_json}
        r.xadd(_try_stream_key(try_id), try_event, maxlen=MAXLEN, approximate=True)
        r.set(_try_latest_key(try_id), payload_json)

        # ✅ 집계 업데이트: frames[0]만 사용
        frame0 = payload.frames[0]
        key = _agg_key(try_id)
        pipe = r.pipeline()
        trlf = _get_by_path(frame0, "deg.mid.trunk_rotation_lateral_flexion")
        
        #pipe = r.pipeline()

        log.info("try=%s trunk_rotation_lateral_flexion=%s frame_idx=%s ip=%s", try_id, trlf, frame0.get("frame_idx"), client_ip)
        lx = _get_by_path(frame0, "position.left.left_ankle.x")
        ly = _get_by_path(frame0, "position.left.left_ankle.y")
        lz = _get_by_path(frame0, "position.left.left_ankle.z")

        rx = _get_by_path(frame0, "position.right.right_ankle.x")
        ry = _get_by_path(frame0, "position.right.right_ankle.y")
        rz = _get_by_path(frame0, "position.right.right_ankle.z")
        
        if lx is not None and ly is not None and lz is not None:
            # 이전 좌표 읽기
            prev = r.hmget(key, ["prev.l_ankle.x", "prev.l_ankle.y", "prev.l_ankle.z"])
            if prev[0] is not None and prev[1] is not None and prev[2] is not None:
                px, py, pz = float(prev[0]), float(prev[1]), float(prev[2])
                d = _dist3((lx, ly, lz), (px, py, pz))

                pipe.hincrbyfloat(key, "sum.l_ankle_jitter", d)
                pipe.hincrbyfloat(key, "sum_sq.l_ankle_jitter", d*d)  # 분산/표준편차용
                pipe.hincrby(key, "count.l_ankle_jitter", 1)

                cur_max = r.hget(key, "max.l_ankle_jitter")
                if cur_max is None or d > float(cur_max):
                    pipe.hset(key, "max.l_ankle_jitter", d)

            # 현재 좌표를 prev로 저장(다음 프레임 대비)
            pipe.hset(key, mapping={
                "prev.l_ankle.x": lx,
                "prev.l_ankle.y": ly,
                "prev.l_ankle.z": lz,
            })

        if rx is not None and ry is not None and rz is not None:
            # 이전 좌표 읽기
            prev = r.hmget(key, ["prev.r_ankle.x", "prev.r_ankle.y", "prev.r_ankle.z"])
            if prev[0] is not None and prev[1] is not None and prev[2] is not None:
                px, py, pz = float(prev[0]), float(prev[1]), float(prev[2])
                d = _dist3((rx, ry, rz), (px, py, pz))

                pipe.hincrbyfloat(key, "sum.r_ankle_jitter", d)
                pipe.hincrbyfloat(key, "sum_sq.r_ankle_jitter", d*d)  # 분산/표준편차용
                pipe.hincrby(key, "count.r_ankle_jitter", 1)

                cur_max = r.hget(key, "max.r_ankle_jitter")
                if cur_max is None or d > float(cur_max):
                    pipe.hset(key, "max.r_ankle_jitter", d)

            # 현재 좌표를 prev로 저장(다음 프레임 대비)
            pipe.hset(key, mapping={
                "prev.r_ankle.x": rx,
                "prev.r_ankle.y": ry,
                "prev.r_ankle.z": rz,
            })

        pipe.execute()
        
        values: Dict[str, float] = {}
        for metric_name, path in METRIC_PATHS.items():
            v = _get_by_path(frame0, path)
            if v is not None:
                values[metric_name] = v

        if values:
            # 2) min/max 현재값을 한 번에 읽기
            min_fields = [f"min.{m}" for m in values.keys()]
            max_fields = [f"max.{m}" for m in values.keys()]
            cur_mins = r.hmget(key, min_fields)
            cur_maxs = r.hmget(key, max_fields)

            pipe = r.pipeline()

            # 3) sum/count는 무조건 업데이트
            for m, v in values.items():
                pipe.hincrbyfloat(key, f"sum.{m}", v)
                pipe.hincrby(key, f"count.{m}", 1)

            # 4) min/max는 비교 후 필요할 때만 set
            for i, (m, v) in enumerate(values.items()):
                cur_min = cur_mins[i]
                if cur_min is None or v < float(cur_min):
                    pipe.hset(key, f"min.{m}", v)

                cur_max = cur_maxs[i]
                if cur_max is None or v > float(cur_max):
                    pipe.hset(key, f"max.{m}", v)

            pipe.execute()

    return {"ok": True, "stream": STREAM_KEY, "id": msg_id, "active_try": try_id}
