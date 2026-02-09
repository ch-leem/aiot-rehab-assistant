import math
from typing import Optional, Mapping, Any
import cv2
import numpy as np


def fmt_deg(v: float) -> str:
    return "nan" if (v is None or not np.isfinite(v)) else f"{v:6.1f}"

def put_lines(img, x: int, y: int, lines, scale=0.6, thickness=2, line_gap=22):
    for i, s in enumerate(lines):
        cv2.putText(img, s, (x, y + i * line_gap),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 255, 255), thickness)

def _finite_xyz(xyz: Optional[np.ndarray]) -> bool:
    if xyz is None:
        return False
    return bool(np.isfinite(xyz).all())

def angle_3pts(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    if not _finite_xyz(a) or not _finite_xyz(b) or not _finite_xyz(c):
        return float("nan")
    ba = a - b
    bc = c - b
    nba = float(np.linalg.norm(ba))
    nbc = float(np.linalg.norm(bc))
    if nba < 1e-6 or nbc < 1e-6:
        return float("nan")
    cosang = float(np.dot(ba, bc) / (nba * nbc))
    cosang = max(-1.0, min(1.0, cosang))
    return math.degrees(math.acos(cosang))

def slope_xy(p1: np.ndarray, p2: np.ndarray, eps: float = 1e-6) -> float:
    if not _finite_xyz(p1) or not _finite_xyz(p2):
        return float("nan")
    d = p2 - p1
    dx = float(d[0])
    dy = float(d[1])
    if abs(dx) < eps and abs(dy) < eps:
        return float("nan")
    return math.degrees(math.atan2(dy, dx))

def center(p1, p2):
    if _finite_xyz(p1) and _finite_xyz(p2):
        return 0.5 * (p1 + p2)
    return float("nan")

def slope_yz(p1: np.ndarray, p2: np.ndarray, eps: float = 1e-6) -> float:
    if not _finite_xyz(p1) or not _finite_xyz(p2):
        return float("nan")
    d = p2 - p1
    dy = float(d[1])
    dz = float(d[2])
    if abs(dy) < eps and abs(dz) < eps:
        return float("nan")
    return math.degrees(math.atan2(dz, dy))
