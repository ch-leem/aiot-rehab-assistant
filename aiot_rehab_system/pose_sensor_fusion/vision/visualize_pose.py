from dataclasses import dataclass
import math
from typing import Optional
import cv2
import numpy as np

# =========================
# Geometry, drawing
# =========================
COCO = {
    "NOSE": 0,
    "L_EYE": 1,
    "R_EYE": 2,
    "L_EAR": 3,
    "R_EAR": 4,
    "L_SHOULDER": 5,
    "R_SHOULDER": 6,
    "L_ELBOW": 7,
    "R_ELBOW": 8,
    "L_WRIST": 9,
    "R_WRIST": 10,
    "L_HIP": 11,
    "R_HIP": 12,
    "L_KNEE": 13,
    "R_KNEE": 14,
    "L_ANKLE": 15,
    "R_ANKLE": 16,
}

COCO_EDGES = [
    (5, 7), (7, 9),
    (6, 8), (8, 10),
    (5, 6),
    (5, 11), (6, 12),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (0, 1), (0, 2), (1, 3), (2, 4)
]

def draw_pose_2d(img: np.ndarray, kpts_xy: np.ndarray, kp_th: float = 0.25):
    for (x, y, s) in kpts_xy:
        if float(s) >= kp_th:
            cv2.circle(img, (int(x), int(y)), 3, (0, 255, 0), -1)
    for a, b in COCO_EDGES:
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