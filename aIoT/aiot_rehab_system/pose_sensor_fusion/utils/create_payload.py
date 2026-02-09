import json
import copy
from typing import Any, Dict, Optional, List
import numpy as np

# 21 keypoints, dataset yaml 순서와 동일
KPT = {
    "nose": 0,
    "left_eye": 1,
    "right_eye": 2,
    "left_ear": 3,
    "right_ear": 4,
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_elbow": 7,
    "right_elbow": 8,
    "left_wrist": 9,
    "right_wrist": 10,
    "left_hip": 11,
    "right_hip": 12,
    "left_knee": 13,
    "right_knee": 14,
    "left_ankle": 15,
    "right_ankle": 16,
    "left_heel": 17,
    "right_heel": 18,
    "left_toe": 19,
    "right_toe": 20,
}

LEFT_KEYS = [
    "left_eye","left_ear","left_shoulder","left_elbow","left_wrist",
    "left_hip","left_knee","left_ankle","left_heel","left_toe"
]
RIGHT_KEYS = [
    "right_eye","right_ear","right_shoulder","right_elbow","right_wrist",
    "right_hip","right_knee","right_ankle","right_heel","right_toe"
]
MID_KEYS = ["nose"]

def load_data_payload(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)

def _pt(x=None, y=None, z=None, conf=None) -> Dict[str, Any]:
    return {"x": x, "y": y, "z": z, "conf": conf}

def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        xf = float(x)
    except Exception:
        return None
    if not np.isfinite(xf):
        return None
    return xf

def build_frame_from_pose(
    payload_template: Dict[str, Any],
    frame_idx: int,
    video_ms: Optional[float],
    host_ms: Optional[float],
    joint_xyz: List[Optional[np.ndarray]],  # length >= 21, each (3,) or None
    joint_conf: List[Optional[float]],      # length >= 21
    deg_left: Dict[str, Any],
    deg_right: Dict[str, Any],
    deg_mid: Dict[str, Any],
    strength: Optional[float],
    power: Optional[float],
) -> Dict[str, Any]:
    """
    payload_template: 너가 준 JSON 스키마 템플릿( frames[0] 구조 )을 load_data_payload로 읽은 것
    반환: frames[0] 한 프레임 dict (템플릿을 deep copy 해서 값만 채움)
    """
    # 템플릿을 프레임 단위로 복사
    tpl0 = payload_template["frames"][0]
    frame = copy.deepcopy(tpl0)

    frame["frame_idx"] = int(frame_idx)
    frame["ts"]["video_ms"] = _to_float(video_ms)
    frame["ts"]["host_ms"] = _to_float(host_ms)

    frame["deg"]["left"] = deg_left
    frame["deg"]["right"] = deg_right
    frame["deg"]["mid"] = deg_mid

    frame["sensor"]["strength"] = _to_float(strength)
    frame["sensor"]["power"] = _to_float(power)

    def fill(side: str, name: str):
        idx = KPT[name]
        xyz = joint_xyz[idx] if idx < len(joint_xyz) else None
        conf = joint_conf[idx] if idx < len(joint_conf) else None

        if xyz is None:
            frame["position"][side][name] = _pt(None, None, None, _to_float(conf))
        else:
            frame["position"][side][name] = _pt(
                _to_float(xyz[0]),
                _to_float(xyz[1]),
                _to_float(xyz[2]),
                _to_float(conf),
            )

    for name in LEFT_KEYS:
        fill("left", name)
    for name in RIGHT_KEYS:
        fill("right", name)
    for name in MID_KEYS:
        fill("mid", name)

    return frame
