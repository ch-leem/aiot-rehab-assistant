import math
import numpy as np
import cv2
from typing import Optional, Tuple, List


def to_float(x) -> float:
    if x is None:
        return math.nan
    s = str(x).strip()
    if s == "" or s.lower() in ("nan", "none", "null"):
        return math.nan
    try:
        return float(s)
    except Exception:
        return math.nan


def make_panel(w: int, h: int, bg: int = 16) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (bg, bg, bg)
    return img


def draw_card(
    img: np.ndarray,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    radius: int = 18,
    color: Tuple[int, int, int] = (28, 28, 28),
    border: Tuple[int, int, int] = (55, 55, 55),
) -> None:
    cv2.rectangle(img, (x0 + radius, y0), (x1 - radius, y1), color, -1)
    cv2.rectangle(img, (x0, y0 + radius), (x1, y1 - radius), color, -1)
    cv2.circle(img, (x0 + radius, y0 + radius), radius, color, -1)
    cv2.circle(img, (x1 - radius, y0 + radius), radius, color, -1)
    cv2.circle(img, (x0 + radius, y1 - radius), radius, color, -1)
    cv2.circle(img, (x1 - radius, y1 - radius), radius, color, -1)
    cv2.rectangle(img, (x0, y0), (x1, y1), border, 1)


def plot_timeseries(
    img: np.ndarray,
    ts_s: List[float],
    ys: List[float],
    title: str,
    y_label: str,
    color_line_bgr: Tuple[int, int, int],
    y_min: Optional[float] = None,
    y_max: Optional[float] = None,
) -> None:
    h, w = img.shape[:2]
    img[:] = (22, 22, 22)
    pad_l, pad_r, pad_t, pad_b = 56, 18, 42, 34

    draw_card(img, 8, 8, w - 8, h - 8, radius=18)

    x0, y0 = pad_l, pad_t
    x1, y1 = w - pad_r, h - pad_b

    cv2.line(img, (x0, y1), (x1, y1), (90, 90, 90), 1, cv2.LINE_AA)
    cv2.line(img, (x0, y0), (x0, y1), (90, 90, 90), 1, cv2.LINE_AA)

    if len(ts_s) < 2:
        cv2.putText(img, title, (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (235, 235, 235), 2, cv2.LINE_AA)
        return

    t0, t1 = float(ts_s[0]), float(ts_s[-1])
    if t1 <= t0:
        t1 = t0 + 1e-6

    y_arr = np.array(ys, dtype=np.float64)
    y_valid = y_arr[np.isfinite(y_arr)]
    if y_valid.size == 0:
        y_valid = np.array([0.0], dtype=np.float64)

    if y_min is None:
        y_min = float(np.percentile(y_valid, 5))
    if y_max is None:
        y_max = float(np.percentile(y_valid, 95))
    if abs(y_max - y_min) < 1e-9:
        y_max = y_min + 1.0

    for k in range(1, 5):
        yy = int(y0 + (y1 - y0) * k / 5.0)
        cv2.line(img, (x0, yy), (x1, yy), (45, 45, 45), 1, cv2.LINE_AA)

    def map_xy(t, v):
        tx = (float(t) - t0) / (t1 - t0)
        tx = max(0.0, min(1.0, tx))
        px = x0 + int((x1 - x0) * tx)

        vv = float(v)
        if not math.isfinite(vv):
            return None

        ty = (vv - y_min) / (y_max - y_min)
        ty = max(0.0, min(1.0, ty))
        py = y1 - int((y1 - y0) * ty)
        return px, py

    pts = []
    for t, v in zip(ts_s, ys):
        p = map_xy(t, v)
        if p is None:
            continue
        pts.append(p)

    if len(pts) >= 2:
        cv2.polylines(img, [np.array(pts, dtype=np.int32)], False, color_line_bgr, 2, cv2.LINE_AA)

    cv2.putText(img, title, (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (235, 235, 235), 2, cv2.LINE_AA)
    cv2.putText(img, y_label, (18, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (180, 180, 180), 2, cv2.LINE_AA)
    cv2.putText(img, f"{y_max:.2f}", (12, y0 + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA)
    cv2.putText(img, f"{y_min:.2f}", (12, y1 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA)
