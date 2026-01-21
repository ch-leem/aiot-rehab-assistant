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
    outlier_mad_k: float = 3.5
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
    vals = patch.reshape(-1)
    vals = vals[vals > 0]

    if vals.size == 0:
        return DepthSample(None, None, False, "no depth")

    if (vals.size / patch.size) < min_valid_ratio:
        return DepthSample(None, None, False, "too few valid")

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