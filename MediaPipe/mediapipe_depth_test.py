import time
import math
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

import cv2
import numpy as np

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from realsense_ai_api import RealSenseAIApi, FrameBundle, Intrinsics

WINDOW_NAME = "MediaPipe Pose"

# =========================
#  One Euro Filter
# =========================
class OneEuroFilter1D:
    def __init__(self, min_cutoff=1.5, beta=0.02, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    @staticmethod
    def _alpha(cutoff_hz: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff_hz)
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def __call__(self, x: float, t: float) -> float:
        if self.t_prev is None or self.x_prev is None:
            self.t_prev = t
            self.x_prev = float(x)
            self.dx_prev = 0.0
            return float(x)

        dt = max(t - self.t_prev, 1e-6)

        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)

        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat


class OneEuroFilter3D:
    def __init__(self, min_cutoff=1.5, beta=0.02, d_cutoff=1.0):
        self.fx = OneEuroFilter1D(min_cutoff, beta, d_cutoff)
        self.fy = OneEuroFilter1D(min_cutoff, beta, d_cutoff)
        self.fz = OneEuroFilter1D(min_cutoff, beta, d_cutoff)

    def reset(self):
        self.fx.reset(); self.fy.reset(); self.fz.reset()

    def __call__(self, xyz: np.ndarray, t: float) -> np.ndarray:
        x, y, z = float(xyz[0]), float(xyz[1]), float(xyz[2])
        return np.array([self.fx(x, t), self.fy(y, t), self.fz(z, t)], dtype=np.float32)


# =========================
#  Depth + 3D helpers (no pyrealsense2 needed)
# =========================
@dataclass
class DepthSample:
    z_m: Optional[float]
    xyz_m: Optional[np.ndarray]   # (3,)
    valid: bool
    debug: str = ""


def deproject_pixel_to_point_pinhole(intr: Intrinsics, u: int, v: int, z_m: float) -> np.ndarray:
    """
    Simple pinhole deprojection (ignores distortion).
    X = (u - ppx)/fx * Z
    Y = (v - ppy)/fy * Z
    Z = Z
    """
    X = (float(u) - intr.ppx) / intr.fx * float(z_m)
    Y = (float(v) - intr.ppy) / intr.fy * float(z_m)
    Z = float(z_m)
    return np.array([X, Y, Z], dtype=np.float32)


def robust_depth_at(
    depth_z16: np.ndarray,
    depth_scale: float,
    intr: Intrinsics,
    u: int, v: int,
    roi: int = 4,
    min_valid_ratio: float = 0.25,
    outlier_mad_k: float = 3.5
) -> DepthSample:
    """
    ROI robust depth:
      - remove zeros
      - median
      - MAD outlier rejection -> median again
    depth_z16: uint16 aligned-to-color depth image
    depth_scale: meters per unit
    """
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
        dbg = "mad reject fallback"
    else:
        final = float(np.median(kept))
        dbg = "mad ok"

    z_m = final * depth_scale
    xyz = deproject_pixel_to_point_pinhole(intr, u, v, z_m)
    return DepthSample(z_m, xyz, True, dbg)


# =========================
#  MediaPipe Pose (Tasks) async wrapper
# =========================
class PoseLandmarkerAsync:
    def __init__(self, model_path: str, num_poses: int = 1):
        self.model_path = model_path
        self.num_poses = num_poses
        self.landmarker = None

        self._lock = threading.Lock()
        self._latest = None
        self._latest_ts = -1

    def _callback(self, result: vision.PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        with self._lock:
            if timestamp_ms >= self._latest_ts:
                self._latest = result
                self._latest_ts = timestamp_ms

    def start(self):
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.LIVE_STREAM,
            num_poses=self.num_poses,
            result_callback=self._callback,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)

    def close(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None

    def submit_bgr(self, frame_bgr: np.ndarray, ts_ms: int):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self.landmarker.detect_async(mp_image, ts_ms)

    def get_latest(self):
        with self._lock:
            return self._latest, self._latest_ts


# =========================
#  Geometry: angles, speed
# =========================
def angle_3pts(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba < 1e-6 or nbc < 1e-6:
        return float("nan")
    cosang = float(np.dot(ba, bc) / (nba * nbc))
    cosang = max(-1.0, min(1.0, cosang))
    return math.degrees(math.acos(cosang))


@dataclass
class JointState:
    xyz_raw: Optional[np.ndarray]
    xyz_filt: Optional[np.ndarray]
    v_xyz: Optional[np.ndarray]
    speed: Optional[float]
    valid: bool


# =========================
#  MediaPipe Pose indices
# =========================
MP_LM = mp.solutions.pose.PoseLandmark
IDX = {
    "LEFT_SHOULDER": int(MP_LM.LEFT_SHOULDER),
    "RIGHT_SHOULDER": int(MP_LM.RIGHT_SHOULDER),
    "LEFT_ELBOW": int(MP_LM.LEFT_ELBOW),
    "RIGHT_ELBOW": int(MP_LM.RIGHT_ELBOW),
    "LEFT_WRIST": int(MP_LM.LEFT_WRIST),
    "RIGHT_WRIST": int(MP_LM.RIGHT_WRIST),
    "LEFT_HIP": int(MP_LM.LEFT_HIP),
    "RIGHT_HIP": int(MP_LM.RIGHT_HIP),
    "LEFT_KNEE": int(MP_LM.LEFT_KNEE),
    "RIGHT_KNEE": int(MP_LM.RIGHT_KNEE),
    "LEFT_ANKLE": int(MP_LM.LEFT_ANKLE),
    "RIGHT_ANKLE": int(MP_LM.RIGHT_ANKLE),
}
POSE_CONNECTIONS = mp.solutions.pose.POSE_CONNECTIONS


def draw_pose_fast(img_bgr: np.ndarray, lms_norm: List, color=(0, 255, 0)):
    h, w = img_bgr.shape[:2]
    for lm in lms_norm:
        u = int(lm.x * w)
        v = int(lm.y * h)
        if 0 <= u < w and 0 <= v < h:
            cv2.circle(img_bgr, (u, v), 2, color, -1)
    for a, b in POSE_CONNECTIONS:
        la, lb = lms_norm[a], lms_norm[b]
        ua, va = int(la.x * w), int(la.y * h)
        ub, vb = int(lb.x * w), int(lb.y * h)
        if 0 <= ua < w and 0 <= va < h and 0 <= ub < w and 0 <= vb < h:
            cv2.line(img_bgr, (ua, va), (ub, vb), color, 1)


# =========================
#  Main
# =========================
def main():
    MODEL_PATH = "./model/pose_landmarker_heavy.task"

    DEPTH_ROI = 5
    VIS_TH = 0.5

    FILTER_MIN_CUTOFF = 1.5
    FILTER_BETA = 0.02
    FILTER_D_CUTOFF = 1.0

    pose = PoseLandmarkerAsync(MODEL_PATH, num_poses=1)
    pose.start()

    filters: Dict[int, OneEuroFilter3D] = {
        i: OneEuroFilter3D(FILTER_MIN_CUTOFF, FILTER_BETA, FILTER_D_CUTOFF) for i in range(33)
    }
    prev_filt: Dict[int, Tuple[np.ndarray, float]] = {}

    fps_ema = 0.0
    last_t = time.time()

    # ✅ RealSenseAIApi 사용 (align_depth_to="color" 중요)
    with RealSenseAIApi(
        rgb_size=(640, 480),
        depth_size=(640, 480),
        fps=30,
        enable_depth=True,
        align_depth_to="color",
        rgb_format="bgr",
        depth_hole_filling=1,
        depth_decimation=1,
        timeout_ms=2000,
    ) as cam:

        intr = cam.rgb_intrinsics()        # our Intrinsics dataclass
        depth_scale = cam.depth_scale()    # meters per unit
        if depth_scale is None:
            raise RuntimeError("Depth scale is None. Depth stream not enabled?")

        while True:
            # frame acquisition
            bundle: FrameBundle = cam.get_frames(want_depth_frame=True, postprocess_depth=False)
            color_bgr = bundle.rgb
            depth_z16 = bundle.depth  # aligned depth (uint16)
            if depth_z16 is None:
                continue

            ts_ms = int(time.time() * 1000)
            pose.submit_bgr(color_bgr, ts_ms)

            result, _ = pose.get_latest()

            out = color_bgr.copy()
            h, w = out.shape[:2]
            joint_states: Dict[int, JointState] = {}

            if result is not None and result.pose_landmarks:
                lms = result.pose_landmarks[0]
                draw_pose_fast(out, lms, color=(0, 255, 0))

                now_t = time.time()

                for i, lm in enumerate(lms):
                    if lm.visibility is not None and lm.visibility < VIS_TH:
                        joint_states[i] = JointState(None, None, None, None, False)
                        continue

                    u = int(lm.x * w)
                    v = int(lm.y * h)

                    ds = robust_depth_at(
                        depth_z16, depth_scale, intr, u, v,
                        roi=DEPTH_ROI,
                        min_valid_ratio=0.25,
                        outlier_mad_k=3.5
                    )

                    if not ds.valid or ds.xyz_m is None:
                        joint_states[i] = JointState(None, None, None, None, False)
                        continue

                    xyz_raw = ds.xyz_m
                    xyz_filt = filters[i](xyz_raw, now_t)

                    if i in prev_filt:
                        xyz_prev, t_prev = prev_filt[i]
                        dt = max(now_t - t_prev, 1e-6)
                        v_xyz = (xyz_filt - xyz_prev) / dt
                        speed = float(np.linalg.norm(v_xyz))
                    else:
                        v_xyz = None
                        speed = None

                    prev_filt[i] = (xyz_filt, now_t)
                    joint_states[i] = JointState(xyz_raw, xyz_filt, v_xyz, speed, True)

                # angles + speed overlay
                def get_f(idx: int) -> Optional[np.ndarray]:
                    js = joint_states.get(idx)
                    return js.xyz_filt if (js and js.valid and js.xyz_filt is not None) else None

                Ls = get_f(IDX["LEFT_SHOULDER"]); Le = get_f(IDX["LEFT_ELBOW"]); Lw = get_f(IDX["LEFT_WRIST"])
                Rs = get_f(IDX["RIGHT_SHOULDER"]); Re = get_f(IDX["RIGHT_ELBOW"]); Rw = get_f(IDX["RIGHT_WRIST"])
                Lh = get_f(IDX["LEFT_HIP"]); Lk = get_f(IDX["LEFT_KNEE"]); La = get_f(IDX["LEFT_ANKLE"])
                Rh = get_f(IDX["RIGHT_HIP"]); Rk = get_f(IDX["RIGHT_KNEE"]); Ra = get_f(IDX["RIGHT_ANKLE"])

                ytxt = 25
                def put(line: str):
                    nonlocal ytxt
                    cv2.putText(out, line, (10, ytxt), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                    ytxt += 22

                if Ls is not None and Le is not None and Lw is not None:
                    put(f"L elbow angle: {angle_3pts(Ls, Le, Lw):.1f} deg")
                if Rs is not None and Re is not None and Rw is not None:
                    put(f"R elbow angle: {angle_3pts(Rs, Re, Rw):.1f} deg")
                if Lh is not None and Lk is not None and La is not None:
                    put(f"L knee angle:  {angle_3pts(Lh, Lk, La):.1f} deg")
                if Rh is not None and Rk is not None and Ra is not None:
                    put(f"R knee angle:  {angle_3pts(Rh, Rk, Ra):.1f} deg")

                Lw_state = joint_states.get(IDX["LEFT_WRIST"])
                Rw_state = joint_states.get(IDX["RIGHT_WRIST"])
                if Lw_state and Lw_state.valid and Lw_state.speed is not None:
                    put(f"L wrist speed: {Lw_state.speed:.3f} m/s")
                if Rw_state and Rw_state.valid and Rw_state.speed is not None:
                    put(f"R wrist speed: {Rw_state.speed:.3f} m/s")

            # FPS
            now = time.time()
            dt = max(now - last_t, 1e-6)
            last_t = now
            fps = 1.0 / dt
            fps_ema = 0.9 * fps_ema + 0.1 * fps

            cv2.putText(out, f"FPS: {fps_ema:.1f}", (10, out.shape[0]-15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            win_name = "Rehab Pose (MediaPipe + RealSense Depth)"
            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_name, 1280, 960) 

            cv2.imshow(win_name, out)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break

    pose.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
