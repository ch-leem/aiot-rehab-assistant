#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
realsense_ai_api.py

Goal
- Provide RGB frames to an AI model.
- When AI returns pixel coordinates (x, y), fetch depth (meters) at that point.
- Provide aligned depth frames (same resolution / pixel grid as RGB),
  so you can also use depth together with RGB (e.g., pose keypoints -> depth).

Key points for pose keypoints
- We align DEPTH -> COLOR grid (rs.align(rs.stream.color)) so (x,y) from RGB can query depth directly.
- We optionally rotate both RGB and depth by 0/90/180/270 deg. AI sees the rotated RGB, so its (x,y) matches rotated depth.
- Depth query uses robust neighborhood sampling (median/nearest/mean/min) and accepts float (YOLO keypoints).

Notes (Jetson / RealSense)
- If you previously needed `python3 -I` to avoid site-packages conflicts, you can run:
    PYTHONNOUSERSITE=1 python3 your_app.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

import numpy as np

try:
    import pyrealsense2 as rs
except ImportError as e:
    raise RuntimeError(
        "pyrealsense2 is not importable. Make sure librealsense python bindings are installed "
        "and you're not picking a conflicting site-packages. Try: PYTHONNOUSERSITE=1 ..."
    ) from e


# -----------------------------------------------------------------------------
# Data types
# -----------------------------------------------------------------------------
@dataclass
class Intrinsics:
    width: int
    height: int
    fx: float
    fy: float
    ppx: float
    ppy: float
    model: str
    coeffs: Tuple[float, float, float, float, float]


@dataclass
class FrameBundle:
    """
    Common container you can pass to your AI pipeline.
    - rgb: HxWx3 uint8 (BGR by default, because OpenCV likes it)
    - depth: HxW uint16 raw depth units (optional) aligned to RGB grid (if enabled)
    """
    rgb: np.ndarray
    depth: Optional[np.ndarray]
    timestamp_ms: float
    color_timestamp_ms: Optional[float] = None
    depth_timestamp_ms: Optional[float] = None
    color_frame_number: Optional[int] = None
    depth_frame_number: Optional[int] = None


# -----------------------------------------------------------------------------
# Main API
# -----------------------------------------------------------------------------
class RealSenseAIApi:
    """
    A small, practical RealSense API for:
      - grabbing RGB frames (for AI)
      - querying depth at pixel coordinates returned by AI (pose keypoints)
      - delivering aligned depth frames (same pixel grid as RGB)
      - optional rotation for portrait/installation
    """

    def __init__(
        self,
        *,
        rgb_size: Tuple[int, int] = (640, 480),    # (W, H)
        depth_size: Tuple[int, int] = (640, 480),  # (W, H)
        fps: int = 30,
        enable_depth: bool = True,
        align_depth_to: str = "color",             # "color" (recommended) or "none"
        rgb_format: str = "bgr",                   # "bgr" or "rgb"
        timeout_ms: int = 2000,

        # rotation of output arrays (AI sees this rotated RGB)
        # 0=no rotation, 1=cw90, 2=180, 3=ccw90
        rotate_90: int = 3,

        # depth post-processing (safe for pixel queries: decimation disabled by default)
        depth_postprocess: bool = False,
        depth_spatial: bool = True,
        depth_temporal: bool = True,
        depth_hole_filling: int = 0,               # 0=off, 1..5
        depth_decimation: int = 1,                 # keep 1 for pose/pixel queries; >1 reduces resolution
    ):
        self.rgb_w, self.rgb_h = int(rgb_size[0]), int(rgb_size[1])
        self.dep_w, self.dep_h = int(depth_size[0]), int(depth_size[1])
        self.fps = int(fps)
        self.enable_depth = bool(enable_depth)
        self.align_depth_to = str(align_depth_to).lower()
        self.rgb_format = str(rgb_format).lower()
        self.timeout_ms = int(timeout_ms)
        self.rotate_90 = int(rotate_90) % 4

        self.depth_postprocess = bool(depth_postprocess)
        self.depth_spatial = bool(depth_spatial)
        self.depth_temporal = bool(depth_temporal)
        self.depth_hole_filling = int(depth_hole_filling)
        self.depth_decimation = int(depth_decimation)

        if self.rgb_format not in ("bgr", "rgb"):
            raise ValueError("rgb_format must be 'bgr' or 'rgb'")

        if self.align_depth_to not in ("color", "none"):
            raise ValueError("align_depth_to must be 'color' or 'none'")

        if self.enable_depth and self.align_depth_to != "color":
            # Pose keypoints use-case: strongly recommended
            # (We don't hard error to keep compatibility, but warn by comment.)
            pass

        self.pipeline = rs.pipeline()
        self.config = rs.config()

        # Streams
        self.config.enable_stream(rs.stream.color, self.rgb_w, self.rgb_h, rs.format.bgr8, self.fps)
        if self.enable_depth:
            self.config.enable_stream(rs.stream.depth, self.dep_w, self.dep_h, rs.format.z16, self.fps)

        # Alignment (depth -> color pixel grid)
        self._align = None
        if self.enable_depth and self.align_depth_to == "color":
            self._align = rs.align(rs.stream.color)

        # Depth filters
        self._dec = rs.decimation_filter()
        self._spat = rs.spatial_filter()
        self._temp = rs.temporal_filter()
        self._hole = rs.hole_filling_filter()

        # Configure filters
        # NOTE: decimation > 1 can break 1:1 pixel queries unless applied before align and you accept changed grid.
        # We'll keep it configurable, but in "pose query" usage you should keep it 1.
        self._dec.set_option(rs.option.filter_magnitude, float(max(1, self.depth_decimation)))
        self._hole.set_option(rs.option.holes_fill, float(max(0, min(5, self.depth_hole_filling))))

        self._profile = None
        self._depth_sensor = None
        self._depth_scale: Optional[float] = None

        self._rgb_intr: Optional[Intrinsics] = None
        self._running = False

    # -------------------------
    # Rotation helpers
    # -------------------------
    def _rotate_np(self, img: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if img is None:
            return None
        k = self.rotate_90
        if k == 0:
            return img
        # np.rot90: k=1 is CCW 90.
        if k == 1:   # right / cw 90
            return np.rot90(img, k=3)
        if k == 2:   # 180
            return np.rot90(img, k=2)
        if k == 3:   # left / ccw 90
            return np.rot90(img, k=1)
        return img

    # -------------------------
    # Lifecycle
    # -------------------------
    def start(self) -> None:
        if self._running:
            return

        self._profile = self.pipeline.start(self.config)
        self._running = True

        # Depth scale (meters per unit)
        if self.enable_depth:
            device = self._profile.get_device()
            self._depth_sensor = device.first_depth_sensor()
            self._depth_scale = float(self._depth_sensor.get_depth_scale())
        else:
            self._depth_scale = None

        # Cache RGB intrinsics (native)
        color_stream = self._profile.get_stream(rs.stream.color).as_video_stream_profile()
        intr = color_stream.get_intrinsics()
        self._rgb_intr = Intrinsics(
            width=int(intr.width),
            height=int(intr.height),
            fx=float(intr.fx),
            fy=float(intr.fy),
            ppx=float(intr.ppx),
            ppy=float(intr.ppy),
            model=str(intr.model),
            coeffs=tuple(float(c) for c in intr.coeffs),
        )

    def stop(self) -> None:
        if not self._running:
            return
        try:
            self.pipeline.stop()
        finally:
            self._running = False

    def __enter__(self) -> "RealSenseAIApi":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    # -------------------------
    # Info
    # -------------------------
    def depth_scale(self) -> Optional[float]:
        return self._depth_scale

    def rgb_intrinsics(self) -> Intrinsics:
        """
        Returns intrinsics matching the *output RGB frame* coordinate system.
        If rotate_90 != 0, width/height/ppx/ppy/fx/fy are transformed accordingly.
        """
        if not self._rgb_intr:
            raise RuntimeError("Camera not started yet. Call start() first.")

        intr = self._rgb_intr
        k = self.rotate_90
        if k == 0:
            return intr

        w, h = intr.width, intr.height
        fx, fy, ppx, ppy = intr.fx, intr.fy, intr.ppx, intr.ppy

        if k == 1:  # cw 90: (x,y)->(y, w-1-x)
            new_ppx = ppy
            new_ppy = (w - 1) - ppx
            return Intrinsics(width=h, height=w, fx=fy, fy=fx, ppx=new_ppx, ppy=new_ppy, model=intr.model, coeffs=intr.coeffs)

        if k == 3:  # ccw 90: (x,y)->(h-1-y, x)
            new_ppx = (h - 1) - ppy
            new_ppy = ppx
            return Intrinsics(width=h, height=w, fx=fy, fy=fx, ppx=new_ppx, ppy=new_ppy, model=intr.model, coeffs=intr.coeffs)

        if k == 2:  # 180: (x,y)->(w-1-x, h-1-y)
            new_ppx = (w - 1) - ppx
            new_ppy = (h - 1) - ppy
            return Intrinsics(width=w, height=h, fx=fx, fy=fy, ppx=new_ppx, ppy=new_ppy, model=intr.model, coeffs=intr.coeffs)

        return intr

    # -------------------------
    # Depth post-processing
    # -------------------------
    def _postprocess_depth(self, depth_frame: rs.depth_frame) -> rs.depth_frame:
        """
        Depth post-processing chain.
        IMPORTANT:
          - If you need pixel-accurate queries on the COLOR grid, avoid decimation > 1.
          - This function does not change alignment by itself. We'll apply postprocess BEFORE align
            to keep the align stage consistent.
        """
        f = depth_frame

        # Decimation (optional). For pose/pixel queries: recommend keep magnitude=1.
        if self.depth_decimation > 1:
            f = self._dec.process(f)

        if self.depth_spatial:
            f = self._spat.process(f)

        if self.depth_temporal:
            f = self._temp.process(f)

        if self.depth_hole_filling > 0:
            f = self._hole.process(f)

        return f

    # -------------------------
    # Frame acquisition
    # -------------------------
    def get_frames(
        self,
        *,
        want_depth_frame: bool = True,
        postprocess_depth: Optional[bool] = None,
    ) -> FrameBundle:
        """
        Returns:
          FrameBundle.rgb : np.ndarray HxWx3 uint8 (BGR or RGB depending on rgb_format)
          FrameBundle.depth : np.ndarray HxW uint16 (aligned to RGB if align_depth_to='color'), or None
        """
        if not self._running:
            raise RuntimeError("Camera not started. Call start() first.")

        if postprocess_depth is None:
            postprocess_depth = self.depth_postprocess

        frames = self.pipeline.wait_for_frames(self.timeout_ms)

        # If we postprocess, do it on the DEPTH frame first (native depth stream),
        # then put it back into frameset by building a composite frameset is not supported directly.
        # So we do: extract depth_frame, process it, and use it separately.
        # Alignment will be performed on a frameset, so we handle this carefully:
        #
        # Strategy:
        # - If no postprocess: align frameset directly (simple).
        # - If postprocess:
        #   - take depth frame, postprocess -> depth_f
        #   - align requires frameset; easiest safe path is:
        #       - align frameset first to get aligned depth
        #       - then apply ONLY non-res-changing filters (spatial/temporal/hole) on aligned depth
        #   - BUT decimation can change resolution -> we keep decimation>1 discouraged for keypoints.
        #
        # Implemented:
        # - Always align frameset first (if enabled)
        # - Then optionally postprocess on the aligned depth frame, with a safety guard:
        #     if depth_decimation>1 and postprocess_depth: force it to 1 for aligned processing.
        #   (so you don't accidentally break 1:1 grid)
        if self.enable_depth and want_depth_frame and (self._align is not None):
            frames = self._align.process(frames)

        color_frame = frames.get_color_frame()
        if not color_frame:
            raise RuntimeError("No color frame received.")

        color_ts_ms = float(color_frame.get_timestamp())
        color_frame_no = int(color_frame.get_frame_number())

        rgb = np.asanyarray(color_frame.get_data())  # BGR8 view

        if self.rgb_format == "rgb":
            rgb = rgb[:, :, ::-1]
        # Freeze frame snapshot: avoid SDK buffer reuse across next waits.
        rgb = np.ascontiguousarray(rgb).copy()

        depth_np = None
        depth_ts_ms = None
        depth_frame_no = None
        if self.enable_depth and want_depth_frame:
            depth_frame = frames.get_depth_frame()
            if depth_frame:
                depth_ts_ms = float(depth_frame.get_timestamp())
                depth_frame_no = int(depth_frame.get_frame_number())
                if postprocess_depth:
                    # Safety: keep pixel grid for pose queries.
                    # Applying decimation here can break 1:1 mapping. Force decimation=1 on aligned frame.
                    original_dec = self.depth_decimation
                    try:
                        self.depth_decimation = 1
                        self._dec.set_option(rs.option.filter_magnitude, 1.0)
                        depth_frame = self._postprocess_depth(depth_frame)
                    finally:
                        # restore
                        self.depth_decimation = original_dec
                        self._dec.set_option(rs.option.filter_magnitude, float(max(1, original_dec)))

                depth_np = np.ascontiguousarray(np.asanyarray(depth_frame.get_data())).copy()

        # Apply rotation to BOTH so AI (x,y) works on rotated depth too
        rgb = self._rotate_np(rgb)
        depth_np = self._rotate_np(depth_np)

        return FrameBundle(
            rgb=rgb,
            depth=depth_np,
            timestamp_ms=color_ts_ms,
            color_timestamp_ms=color_ts_ms,
            depth_timestamp_ms=depth_ts_ms,
            color_frame_number=color_frame_no,
            depth_frame_number=depth_frame_no,
        )

    # -------------------------
    # Depth query at pixel
    # -------------------------
    def depth_at_pixel_m(
        self,
        x: float,
        y: float,
        *,
        frames: Optional[FrameBundle] = None,
        fallback_window: int = 3,
        fallback_mode: str = "median",   # "nearest" | "min" | "median" | "mean"
        min_depth_m: float = 0.05,
        max_depth_m: float = 10.0,
    ) -> Optional[float]:
        """
        Get depth in meters at pixel (x, y) on the RGB-aligned (and rotated) grid.

        - x,y can be float (e.g., YOLO keypoints). We'll round to nearest pixel.
        - fallback_window > 0: search neighborhood for valid depth samples.
        - fallback_mode:
            - "nearest": nearest valid pixel by distance (good for holes)
            - "min": minimum depth in window (can be jumpy)
            - "median": robust for pose keypoints (recommended)
            - "mean": average of valid samples
        """
        if not self.enable_depth:
            return None
        if self._depth_scale is None:
            raise RuntimeError("Depth scale unavailable. Start camera first.")

        if frames is None:
            frames = self.get_frames(want_depth_frame=True)

        if frames.depth is None:
            return None

        h, w = frames.depth.shape[:2]

        xi = int(np.rint(float(x)))
        yi = int(np.rint(float(y)))

        if xi < 0 or yi < 0 or xi >= w or yi >= h:
            return None

        def valid_z_from_raw(d_raw: int) -> Optional[float]:
            if d_raw <= 0:
                return None
            z = d_raw * self._depth_scale
            if z < float(min_depth_m) or z > float(max_depth_m):
                return None
            return float(z)

        # direct pixel
        z0 = valid_z_from_raw(int(frames.depth[yi, xi]))
        if z0 is not None:
            return z0

        if fallback_window <= 0:
            return None

        r = int(fallback_window)
        xs = range(max(0, xi - r), min(w, xi + r + 1))
        ys = range(max(0, yi - r), min(h, yi + r + 1))

        zs = []
        nearest = None  # (dist2, z)

        mode = fallback_mode.lower().strip()

        for yy in ys:
            for xx in xs:
                z = valid_z_from_raw(int(frames.depth[yy, xx]))
                if z is None:
                    continue
                zs.append(z)
                if mode == "nearest":
                    d2 = (xx - xi) * (xx - xi) + (yy - yi) * (yy - yi)
                    if nearest is None or d2 < nearest[0]:
                        nearest = (d2, z)

        if not zs:
            return None

        if mode == "nearest":
            return nearest[1] if nearest is not None else None
        if mode == "min":
            return float(min(zs))
        if mode == "mean":
            return float(sum(zs) / len(zs))
        # default: median
        return float(np.median(np.array(zs, dtype=np.float32)))

    # -------------------------
    # Convenience helpers for AI
    # -------------------------
    def pack_for_ai(
        self,
        *,
        include_depth: bool = False,
        postprocess_depth: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Returns a dict you can feed into your AI code.

        Example:
          pkt = cam.pack_for_ai(include_depth=True)
          rgb = pkt["rgb"]  # np.uint8 HxWx3 (rotated if rotate_90!=0)
          # AI returns (x, y) on this rgb
          z = cam.depth_at_pixel_m(x, y, frames=pkt["bundle"])
        """
        bundle = self.get_frames(
            want_depth_frame=include_depth,
            postprocess_depth=postprocess_depth,
        )
        out = {
            "rgb": bundle.rgb,
            "timestamp_ms": bundle.timestamp_ms,
            "bundle": bundle,  # keep bundle for depth lookup
        }
        if include_depth:
            out["depth"] = bundle.depth
            out["depth_scale"] = self._depth_scale
        return out


# -----------------------------------------------------------------------------
# Demo / sanity check
# -----------------------------------------------------------------------------
def _demo():
    """
    Click-to-measure demo:
      - Show RGB
      - Click a pixel on the RGB window
      - Overlay the depth (meters) at that pixel
      - Press 'q' to quit
    """
    import cv2

    click = {"x": None, "y": None, "z": None, "ts": None}

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            click["x"] = float(x)
            click["y"] = float(y)

    with RealSenseAIApi(
        rgb_size=(640, 480),
        depth_size=(640, 480),
        fps=30,
        enable_depth=True,
        align_depth_to="color",
        rgb_format="bgr",

        #rotate_90=3,              # 1=cw90, 3=ccw90
        depth_postprocess=False,  # for pixel query, usually keep False (or True without decimation)
        depth_hole_filling=1,
        depth_decimation=1,
    ) as cam:
        win = "RGB (click to measure depth)"
        cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(win, on_mouse)

        while True:
            pkt = cam.pack_for_ai(include_depth=True, postprocess_depth=False)
            rgb = pkt["rgb"].copy()
            bundle: FrameBundle = pkt["bundle"]

            if click["x"] is not None and click["y"] is not None:
                z = cam.depth_at_pixel_m(click["x"], click["y"], frames=bundle, fallback_window=3, fallback_mode="median")
                click["z"] = z
                click["ts"] = bundle.timestamp_ms

                cx, cy = int(round(click["x"])), int(round(click["y"]))
                cv2.drawMarker(
                    rgb, (cx, cy), (0, 255, 0),
                    markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2
                )
                text = f"({cx},{cy})  z={z:.3f} m" if z is not None else f"({cx},{cy})  z=None"
                cv2.putText(rgb, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)

            cv2.imshow(win, rgb)

            depth = pkt.get("depth", None)
            if depth is not None:
                depth_vis = cv2.applyColorMap(
                    cv2.convertScaleAbs(depth, alpha=0.03),
                    cv2.COLORMAP_JET,
                )
                cv2.imshow("Depth (aligned)", depth_vis)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    _demo()
