from dataclasses import dataclass
from typing import Optional
from pose_sensor_fusion.vision_utills.realsense_ai_api import Intrinsics
import numpy as np

# =========================
# Depth robust sampling + deprojection (pinhole, no distortion)
# =========================
@dataclass
class DepthSample:
    z_m: Optional[float]
    xyz_m: Optional[np.ndarray]
    valid: bool
    debug: str = ""

def deproject_pixel_to_point_pinhole(intr: Intrinsics, u: int, v: int, z_m: float) -> np.ndarray:
    X = (float(u) - intr.ppx) / intr.fx * float(z_m)
    Y = (float(v) - intr.ppy) / intr.fy * float(z_m)
    Z = float(z_m)
    return np.array([X, Y, Z], dtype=np.float32)

def robust_depth_at(
    depth_z16: np.ndarray,
    depth_scale: float,
    intr: Intrinsics,
    u: int,
    v: int,
    roi: int = 5,
    min_valid_ratio: float = 0.25,
    outlier_mad_k: float = 3.5,
    seed_gate_mm: float = 120.0,
    nearest_k: int = 9,
) -> DepthSample:
    if depth_z16 is None:
        return DepthSample(None, None, False, "no depth frame")

    h, w = depth_z16.shape[:2]
    if u < 0 or v < 0 or u >= w or v >= h:
        return DepthSample(None, None, False, "OOB")

    x0 = max(u - roi, 0)
    x1 = min(u + roi + 1, w)
    y0 = max(v - roi, 0)
    y1 = min(v + roi + 1, h)

    patch = depth_z16[y0:y1, x0:x1].astype(np.float32)
    valid_mask = patch > 0
    vals = patch[valid_mask]

    if vals.size == 0:
        return DepthSample(None, None, False, "no depth")

    if (vals.size / patch.size) < min_valid_ratio:
        return DepthSample(None, None, False, "too few valid")

    final = None
    dbg = ""

    # Prefer samples near center depth to avoid background contamination.
    center_raw = float(depth_z16[v, u]) if (0 <= u < w and 0 <= v < h) else 0.0
    if center_raw > 0:
        gated = vals[np.abs(vals - center_raw) <= float(seed_gate_mm)]
        if gated.size >= 3:
            final = float(np.median(gated))
            dbg = "seed gate"

    # If center is invalid, use nearest valid samples to (u, v).
    if final is None:
        ys_local, xs_local = np.where(valid_mask)
        if ys_local.size > 0:
            xs = xs_local.astype(np.float32) + float(x0)
            ys = ys_local.astype(np.float32) + float(y0)
            d2 = (xs - float(u)) ** 2 + (ys - float(v)) ** 2
            k = max(1, min(int(nearest_k), int(vals.size)))
            nn_idx = np.argpartition(d2, k - 1)[:k]
            near_vals = vals[nn_idx]
            if near_vals.size >= 3:
                final = float(np.median(near_vals))
                dbg = "nearest k"

    # Fallback: global robust median in ROI.
    if final is None:
        med = float(np.median(vals))
        mad = float(np.median(np.abs(vals - med))) + 1e-6
        zscore = np.abs(vals - med) / mad
        kept = vals[zscore < outlier_mad_k]

        if kept.size < max(3, int(vals.size * 0.2)):
            final = med
            dbg = "mad fallback"
        else:
            final = float(np.median(kept))
            dbg = "mad ok"

    z_m = final * depth_scale
    xyz = deproject_pixel_to_point_pinhole(intr, u, v, z_m)
    return DepthSample(z_m, xyz, True, dbg)
