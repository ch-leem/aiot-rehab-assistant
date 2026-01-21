from typing import Optional
import cv2
import numpy as np

# =========================
# Letterbox preprocess + unletterbox
# =========================
def preprocess_bgr_letterbox(frame_bgr: np.ndarray, size: int = 640):
    h, w = frame_bgr.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.zeros((size, size, 3), dtype=np.uint8)
    dx = (size - nw) // 2
    dy = (size - nh) // 2
    canvas[dy:dy + nh, dx:dx + nw] = resized

    x = canvas.astype(np.float32) / 255.0
    x = x.transpose(2, 0, 1)[None, ...]  # (1,3,640,640)
    return x, scale, dx, dy

def unletterbox_points(kpts_640: np.ndarray, scale: float, dx: int, dy: int) -> np.ndarray:
    out = kpts_640.copy()
    out[:, 0] = (out[:, 0] - dx) / (scale + 1e-9)
    out[:, 1] = (out[:, 1] - dy) / (scale + 1e-9)
    return out