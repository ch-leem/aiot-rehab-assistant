#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
realsense_ai_api.py

Goal
- Provide RGB frames to an AI model.
- When AI returns pixel coordinates (x, y), fetch depth (meters) at that point.
- Optionally provide aligned depth frames (same resolution / pixel grid as RGB),
  so you can also feed depth to AI later.

Notes (Jetson / RealSense)
- If you previously needed `python3 -I` to avoid site-packages conflicts, you can run:
    PYTHONNOUSERSITE=1 python3 your_app.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

import time
import numpy as np

try:
    import pyrealsense2 as rs
except ImportError as e:
    raise RuntimeError(
        "pyrealsense2 is not importable. Make sure librealsense python bindings are installed "
        "and you're not picking a conflicting site-packages. Try: PYTHONNOUSERSITE=1 ..."
    ) from e


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
    - depth: HxW uint16 raw depth units (optional)
    - depth_m: callable to query meters at pixel
    """
    rgb: np.ndarray
    depth: Optional[np.ndarray]
    timestamp_ms: float


class RealSenseAIApi:
    """
    A small, practical RealSense API for:
      - grabbing RGB frames (for AI)
      - querying depth at pixel coordinates returned by AI
      - optionally delivering aligned depth frames (same pixel grid as RGB)
    """

    def __init__(
        self,
        *,
        rgb_size: Tuple[int, int] = (640, 480),   # (W, H)
        depth_size: Tuple[int, int] = (640, 480), # (W, H) can be different; alignment will map depth->rgb grid
        fps: int = 30,
        enable_depth: bool = True,
        align_depth_to: str = "color",            # "color" (recommended), or "none"
        rgb_format: str = "bgr",                  # "bgr" or "rgb"
        depth_hole_filling: int = 0,              # 0=off, 1..5 increasing fill
        depth_decimation: int = 1,                # 1=no decimation; 2,4... to downsample depth (then alignment happens)
        timeout_ms: int = 2000,
    ):
        self.rgb_w, self.rgb_h = int(rgb_size[0]), int(rgb_size[1])
        self.dep_w, self.dep_h = int(depth_size[0]), int(depth_size[1])
        self.fps = int(fps)
        self.enable_depth = bool(enable_depth)
        self.align_depth_to = align_depth_to
        self.rgb_format = rgb_format.lower()
        self.timeout_ms = int(timeout_ms)

        if self.rgb_format not in ("bgr", "rgb"):
            raise ValueError("rgb_format must be 'bgr' or 'rgb'")

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

        # Post-processing for depth (optional)
        self._dec = rs.decimation_filter()
        self._spat = rs.spatial_filter()
        self._temp = rs.temporal_filter()
        self._hole = rs.hole_filling_filter()

        # Parameters
        self._dec.set_option(rs.option.filter_magnitude, float(max(1, depth_decimation)))
        self._hole.set_option(rs.option.holes_fill, float(depth_hole_filling))

        self._profile = None
        self._depth_sensor = None
        self._depth_scale = None

        # Cache intrinsics
        self._rgb_intr: Optional[Intrinsics] = None

        self._running = False

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

        # Cache RGB intrinsics
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
    def rgb_intrinsics(self) -> Intrinsics:
        if not self._rgb_intr:
            raise RuntimeError("Camera not started yet. Call start() first.")
        return self._rgb_intr

    def depth_scale(self) -> Optional[float]:
        return self._depth_scale

    # -------------------------
    # Frame acquisition
    # -------------------------
    def _postprocess_depth(self, depth_frame: rs.depth_frame) -> rs.depth_frame:
        """
        Optional depth post-processing chain.
        """
        f = depth_frame
        # Decimation (downsample)
        f = self._dec.process(f)
        # Spatial/Temporal smoothing
        f = self._spat.process(f)
        f = self._temp.process(f)
        # Hole filling
        f = self._hole.process(f)
        return f

    def get_frames(
        self,
        *,
        want_depth_frame: bool = True,
        postprocess_depth: bool = False,
    ) -> FrameBundle:
        """
        Returns:
          FrameBundle.rgb : np.ndarray HxWx3 uint8 (BGR or RGB depending on rgb_format)
          FrameBundle.depth : np.ndarray HxW uint16 (aligned to RGB if align_depth_to='color'), or None
        """
        if not self._running:
            raise RuntimeError("Camera not started. Call start() first.")

        frames = self.pipeline.wait_for_frames(self.timeout_ms)

        if self.enable_depth and want_depth_frame:
            if self._align is not None:
                frames = self._align.process(frames)

        color_frame = frames.get_color_frame()
        if not color_frame:
            raise RuntimeError("No color frame received.")

        rgb = np.asanyarray(color_frame.get_data())  # BGR8
        if self.rgb_format == "rgb":
            # Convert BGR -> RGB without OpenCV dependency
            rgb = rgb[:, :, ::-1].copy()

        depth_np = None
        if self.enable_depth and want_depth_frame:
            depth_frame = frames.get_depth_frame()
            if depth_frame:
                if postprocess_depth:
                    depth_frame = self._postprocess_depth(depth_frame)
                    # If you postprocess after alignment, the result stays aligned,
                    # but note decimation might change resolution. Prefer decimation=1 if you need 1:1 pixels.
                depth_np = np.asanyarray(depth_frame.get_data())

        ts_ms = float(color_frame.get_timestamp())
        return FrameBundle(rgb=rgb, depth=depth_np, timestamp_ms=ts_ms)

    # -------------------------
    # Depth query at pixel
    # -------------------------
    def depth_at_pixel_m(
        self,
        x: int,
        y: int,
        *,
        frames: Optional[FrameBundle] = None,
        fallback_window: int = 0,
    ) -> Optional[float]:
        """
        Get depth in meters at pixel (x, y) on the RGB-aligned grid.

        Recommended usage:
          bundle = cam.get_frames(want_depth_frame=True)
          z = cam.depth_at_pixel_m(x, y, frames=bundle)

        If fallback_window > 0, it will search a small neighborhood for a valid depth (non-zero)
        to handle holes. Example: fallback_window=2 searches (x±2, y±2).
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
        x = int(x)
        y = int(y)
        if x < 0 or y < 0 or x >= w or y >= h:
            return None

        d = int(frames.depth[y, x])
        if d > 0:
            return d * self._depth_scale

        # Optional fallback: local search for nearest non-zero
        if fallback_window > 0:
            r = int(fallback_window)
            best = None
            for yy in range(max(0, y - r), min(h, y + r + 1)):
                for xx in range(max(0, x - r), min(w, x + r + 1)):
                    dd = int(frames.depth[yy, xx])
                    if dd > 0:
                        z = dd * self._depth_scale
                        best = z if best is None else min(best, z)
            return best

        return None

    # -------------------------
    # Convenience helpers for AI
    # -------------------------
    def pack_for_ai(
        self,
        *,
        include_depth: bool = False,
        postprocess_depth: bool = False,
    ) -> Dict[str, Any]:
        """
        Returns a dict you can feed into your AI code.

        Example:
          pkt = cam.pack_for_ai(include_depth=False)
          rgb = pkt["rgb"]  # np.uint8 HxWx3
          # AI returns (x, y)
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
            click["x"] = int(x)
            click["y"] = int(y)
            # z will be updated on next frame (so it uses aligned depth from the same bundle)

    with RealSenseAIApi(
        rgb_size=(640, 480),
        depth_size=(640, 480),
        fps=30,
        enable_depth=True,
        align_depth_to="color",
        rgb_format="bgr",
        depth_hole_filling=1,   # helps holes a bit
        depth_decimation=1,     # keep 1:1 mapping for pixel queries
    ) as cam:
        win = "RGB (click to measure depth)"
        cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(win, on_mouse)

        while True:
            pkt = cam.pack_for_ai(include_depth=True, postprocess_depth=False)
            rgb = pkt["rgb"].copy()
            bundle: FrameBundle = pkt["bundle"]

            # If user clicked, query depth at that pixel on the aligned depth frame
            if click["x"] is not None and click["y"] is not None:
                z = cam.depth_at_pixel_m(click["x"], click["y"], frames=bundle, fallback_window=2)
                click["z"] = z
                click["ts"] = bundle.timestamp_ms

                # Draw marker + text
                cv2.drawMarker(rgb, (click["x"], click["y"]), (0, 255, 0),
                               markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)

                text = f"({click['x']},{click['y']})  z={z:.3f} m" if z is not None else f"({click['x']},{click['y']})  z=None"
                cv2.putText(rgb, text, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)

            cv2.imshow(win, rgb)

            # Optional: show aligned depth visualization too
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
