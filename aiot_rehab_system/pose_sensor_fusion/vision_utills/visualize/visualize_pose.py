from dataclasses import dataclass
import math
from typing import Optional
import cv2
import numpy as np

# =========================
# Geometry, drawing
# =========================
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

KPT_EDGES = [
    (KPT["left_shoulder"], KPT["left_elbow"]),
    (KPT["left_elbow"], KPT["left_wrist"]),
    (KPT["right_shoulder"], KPT["right_elbow"]),
    (KPT["right_elbow"], KPT["right_wrist"]),
    (KPT["left_shoulder"], KPT["right_shoulder"]),

    (KPT["left_shoulder"], KPT["left_hip"]),
    (KPT["right_shoulder"], KPT["right_hip"]),
    (KPT["left_hip"], KPT["right_hip"]),

    (KPT["left_hip"], KPT["left_knee"]),
    (KPT["left_knee"], KPT["left_ankle"]),
    (KPT["right_hip"], KPT["right_knee"]),
    (KPT["right_knee"], KPT["right_ankle"]),

    (KPT["nose"], KPT["left_eye"]),
    (KPT["nose"], KPT["right_eye"]),
    (KPT["left_eye"], KPT["left_ear"]),
    (KPT["right_eye"], KPT["right_ear"]),

    # foot (21)
    (KPT["left_ankle"], KPT["left_heel"]),
    (KPT["left_heel"], KPT["left_toe"]),
    (KPT["right_ankle"], KPT["right_heel"]),
    (KPT["right_heel"], KPT["right_toe"]),
]

# def draw_pose_2d(img: np.ndarray, kpts_xy: np.ndarray, kp_th: float = 0.25):
#     for (x, y, s) in kpts_xy:
#         if float(s) >= kp_th:
#             cv2.circle(img, (int(x), int(y)), 3, (0, 255, 0), -1)
#     for a, b in COCO_EDGES:
#         xa, ya, sa = kpts_xy[a]
#         xb, yb, sb = kpts_xy[b]
#         if float(sa) >= kp_th and float(sb) >= kp_th:
#             cv2.line(img, (int(xa), int(ya)), (int(xb), int(yb)), (255, 0, 0), 2)

def draw_pose_2d(img: np.ndarray, kpts_xy: np.ndarray, kp_th: float = 0.25):
    K = int(kpts_xy.shape[0])

    for (x, y, s) in kpts_xy:
        if float(s) >= kp_th:
            cv2.circle(img, (int(x), int(y)), 3, (0, 255, 0), -1)

    for a, b in KPT_EDGES:
        # 17개만 들어오는 경우에도 안전하게 (구 엔진 대응)
        if a >= K or b >= K:
            continue
        xa, ya, sa = kpts_xy[a]
        xb, yb, sb = kpts_xy[b]
        if float(sa) >= kp_th and float(sb) >= kp_th:
            cv2.line(img, (int(xa), int(ya)), (int(xb), int(yb)), (255, 0, 0), 2)


def angle_3pts(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    nba = float(np.linalg.norm(ba))
    nbc = float(np.linalg.norm(bc))
    if nba < 1e-6 or nbc < 1e-6:
        return float("nan")
    cosang = float(np.dot(ba, bc) / (nba * nbc))
    cosang = max(-1.0, min(1.0, cosang))
    return math.degrees(math.acos(cosang))

@dataclass
class Joint3DState:
    xyz_raw: Optional[np.ndarray]
    xyz_filt: Optional[np.ndarray]
    v_xyz: Optional[np.ndarray]
    speed: Optional[float]
    valid: bool