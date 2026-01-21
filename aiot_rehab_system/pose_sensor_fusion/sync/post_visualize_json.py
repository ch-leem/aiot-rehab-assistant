#!/usr/bin/env python3

import json
import math
import time
import argparse
from collections import deque
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import cv2

from pose_sensor_fusion.utils.config_loader import load_yaml_config
from pose_sensor_fusion.sync.panel.ui_primitives import to_float
from pose_sensor_fusion.sync.panel.panel_pose3d import Pose3DPanel, cam_xyz_to_view
from pose_sensor_fusion.sync.panel.panel_timeseries import TimeseriesPanel
from pose_sensor_fusion.sync.panel.layout_3_panel import compose_three_panel


# 21 keypoint order, dataset yaml 순서와 동일
KPT21 = {
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

# JSON 템플릿 구조에서 관절이 들어있는 위치
# mid: nose
# left: left_*
# right: right_*
KPT21_SRC: List[Tuple[str, str]] = [
    ("mid", "nose"),
    ("left", "left_eye"),
    ("right", "right_eye"),
    ("left", "left_ear"),
    ("right", "right_ear"),
    ("left", "left_shoulder"),
    ("right", "right_shoulder"),
    ("left", "left_elbow"),
    ("right", "right_elbow"),
    ("left", "left_wrist"),
    ("right", "right_wrist"),
    ("left", "left_hip"),
    ("right", "right_hip"),
    ("left", "left_knee"),
    ("right", "right_knee"),
    ("left", "left_ankle"),
    ("right", "right_ankle"),
    ("left", "left_heel"),
    ("right", "right_heel"),
    ("left", "left_toe"),
    ("right", "right_toe"),
]

# Pose3DPanel이 17을 기대할 가능성이 있어서 21 -> 17로 변환해서 렌더
# COCO17 순서: nose, l_eye, r_eye, l_ear, r_ear, l_shoulder, r_shoulder, l_elbow, r_elbow, l_wrist, r_wrist, l_hip, r_hip, l_knee, r_knee, l_ankle, r_ankle
KPT21_TO_COCO17 = [
    KPT21["nose"],
    KPT21["left_eye"],
    KPT21["right_eye"],
    KPT21["left_ear"],
    KPT21["right_ear"],
    KPT21["left_shoulder"],
    KPT21["right_shoulder"],
    KPT21["left_elbow"],
    KPT21["right_elbow"],
    KPT21["left_wrist"],
    KPT21["right_wrist"],
    KPT21["left_hip"],
    KPT21["right_hip"],
    KPT21["left_knee"],
    KPT21["right_knee"],
    KPT21["left_ankle"],
    KPT21["right_ankle"],
]


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pose_sensor_fusion/visualize_replay.yaml")
    ap.add_argument("--ndjson", default=None)
    ap.add_argument("--start_idx", type=int, default=None)
    ap.add_argument("--end_idx", type=int, default=None)
    ap.add_argument("--conf_th", type=float, default=None)
    ap.add_argument("--target_fps", type=float, default=None)
    ap.add_argument("--use_timestamp", action="store_true")
    ap.add_argument("--no_sleep", action="store_true")
    return ap.parse_args()


def load_and_merge_config(config_path: str, args) -> Dict[str, Any]:
    cfg: Dict[str, Any] = load_yaml_config(config_path)

    if args.ndjson is not None:
        cfg["ndjson"]["path"] = args.ndjson
    if args.start_idx is not None:
        cfg["range"]["start_idx"] = int(args.start_idx)
    if args.end_idx is not None:
        cfg["range"]["end_idx"] = int(args.end_idx)
    if args.conf_th is not None:
        cfg["replay"]["conf_th"] = float(args.conf_th)
    if args.target_fps is not None:
        cfg["replay"]["target_fps"] = float(args.target_fps)

    if args.use_timestamp:
        cfg["replay"]["use_timestamp"] = True
    if args.no_sleep:
        cfg["replay"]["no_sleep"] = True

    return cfg


def load_frames_ndjson(path: str) -> List[Dict[str, Any]]:
    frames: List[Dict[str, Any]] = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            frames.append(json.loads(line))
    return frames


def parse_pts21(frame: Dict[str, Any], conf_th: float) -> Tuple[np.ndarray, np.ndarray]:
    pts = np.full((21, 3), np.nan, dtype=np.float32)
    valid = np.zeros((21,), dtype=bool)

    pos = frame.get("position", {}) or {}

    for j, (side, name) in enumerate(KPT21_SRC):
        d = (pos.get(side, {}) or {}).get(name)
        if not isinstance(d, dict):
            continue

        x = to_float(d.get("x"))
        y = to_float(d.get("y"))
        z = to_float(d.get("z"))
        c = to_float(d.get("conf"))

        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z) and math.isfinite(c) and c >= conf_th:
            pts[j] = cam_xyz_to_view((x, y, z))
            valid[j] = True

    return pts, valid


def pts21_to_pts17(pts21: np.ndarray, valid21: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    pts17 = np.full((17, 3), np.nan, dtype=np.float32)
    valid17 = np.zeros((17,), dtype=bool)

    for i17, idx21 in enumerate(KPT21_TO_COCO17):
        pts17[i17] = pts21[idx21]
        valid17[i17] = bool(valid21[idx21])

    return pts17, valid17


def get_ts_seconds(frame: Dict[str, Any], fallback_s: float) -> float:
    ts = frame.get("ts", {}) or {}
    host_ms = to_float(ts.get("host_ms"))
    video_ms = to_float(ts.get("video_ms"))

    if math.isfinite(host_ms):
        return float(host_ms) / 1000.0
    if math.isfinite(video_ms):
        return float(video_ms) / 1000.0
    return fallback_s


def get_strength(frame: Dict[str, Any]) -> float:
    s = to_float((frame.get("sensor", {}) or {}).get("strength"))
    return float(s) if math.isfinite(s) else math.nan


def get_power(frame: Dict[str, Any]) -> float:
    p = to_float((frame.get("sensor", {}) or {}).get("power"))
    return float(p) if math.isfinite(p) else math.nan


def wrist_speed_mps(pts21: np.ndarray, valid21: np.ndarray, pts21_prev: Optional[np.ndarray], valid21_prev: Optional[np.ndarray], dt: float) -> float:
    if pts21_prev is None or valid21_prev is None:
        return math.nan
    if dt <= 1e-6:
        return math.nan

    idx = KPT21["right_wrist"]
    if not bool(valid21[idx]) or not bool(valid21_prev[idx]):
        return math.nan

    p0 = pts21_prev[idx]
    p1 = pts21[idx]
    if not np.isfinite(p0).all() or not np.isfinite(p1).all():
        return math.nan

    v = (p1 - p0) / dt
    return float(np.linalg.norm(v))


def push_window(t_deque: deque, y_deque: deque, t_now: float, y_now: float, window_sec: float) -> None:
    t_deque.append(t_now)
    y_deque.append(y_now)
    t_min = t_now - window_sec
    while len(t_deque) > 0 and t_deque[0] < t_min:
        t_deque.popleft()
        y_deque.popleft()


def main(cfg: Dict[str, Any]) -> None:
    ndjson_path = cfg["ndjson"]["path"]
    if not ndjson_path:
        raise RuntimeError("ndjson.path is empty, use --ndjson or set in config")

    start_idx = int(cfg["range"]["start_idx"])
    end_idx = int(cfg["range"]["end_idx"])

    conf_th = float(cfg["replay"]["conf_th"])
    history_sec = float(cfg["replay"]["history_sec"])
    target_fps = float(cfg["replay"]["target_fps"])
    use_timestamp = bool(cfg["replay"]["use_timestamp"])
    no_sleep = bool(cfg["replay"]["no_sleep"])

    o3d_w = int(cfg["render"]["o3d_w"])
    o3d_h = int(cfg["render"]["o3d_h"])
    win_w = int(cfg["render"]["win_w"])
    win_h = int(cfg["render"]["win_h"])
    left_w = int(cfg["render"]["left_w"])

    strength_cfg = cfg["plot"]["strength"]
    power_cfg = cfg["plot"]["power"]
    speed_cfg = cfg["plot"]["speed"]

    frames = load_frames_ndjson(ndjson_path)
    if not frames:
        raise RuntimeError("ndjson empty")

    s = max(0, start_idx)
    e = end_idx if end_idx >= 0 else len(frames)
    if s >= len(frames):
        raise RuntimeError(f"start_idx {s} >= total frames {len(frames)}")
    frames = frames[s:e]

    # timestamp list
    t_s: List[float] = []
    for i, fr in enumerate(frames):
        t_s.append(get_ts_seconds(fr, fallback_s=float(i) / max(1e-6, target_fps)))

    dt_src = [max(1e-6, t_s[i] - t_s[i - 1]) for i in range(1, len(t_s))]
    median_dt = float(np.median(np.array(dt_src, dtype=np.float64))) if dt_src else (1.0 / target_fps)
    dt_tgt = 1.0 / max(1e-6, target_fps)
    scale = max(1e-6, median_dt / dt_tgt)

    strength_t = deque()
    strength_v = deque()
    power_t = deque()
    power_v = deque()
    speed_t = deque()
    speed_v = deque()

    pose_panel = Pose3DPanel(o3d_w, o3d_h)

    right_w = win_w - left_w
    plot_h = win_h // 2

    strength_panel = TimeseriesPanel(
        right_w,
        plot_h,
        title=str(strength_cfg["title"]),
        y_label=str(strength_cfg["y_label"]),
        y_min=float(strength_cfg["y_min"]),
        y_max=float(strength_cfg["y_max"]),
        color_bgr=tuple(strength_cfg["color_bgr"]),
    )
    power_panel = TimeseriesPanel(
        right_w,
        win_h - plot_h,
        title=str(power_cfg["title"]),
        y_label=str(power_cfg["y_label"]),
        y_min=float(power_cfg["y_min"]),
        y_max=float(power_cfg["y_max"]),
        color_bgr=tuple(power_cfg["color_bgr"]),
    )

    # speed panel은 power 패널에 같이 그릴 수도 있지만, 일단 값은 계산해서 화면 텍스트로도 보여줌
    # 원하면 TimeseriesPanel을 하나 더 추가해서 3개 패널로 바꾸는 것도 가능

    win = "3D + strength/power (q,esc quit, space pause, a,d step)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, win_w, win_h)

    paused = False
    idx = 0
    last_wall = time.time()

    pts21_prev = None
    valid21_prev = None

    try:
        while True:
            if idx >= len(frames):
                paused = True
                idx = len(frames) - 1

            fr = frames[idx]
            ts = t_s[idx]

            pts21, valid21 = parse_pts21(fr, conf_th=conf_th)
            pts17, valid17 = pts21_to_pts17(pts21, valid21)

            strength = get_strength(fr)
            power = get_power(fr)

            dt = (t_s[idx] - t_s[idx - 1]) if idx > 0 else math.nan
            spd = wrist_speed_mps(pts21, valid21, pts21_prev, valid21_prev, float(dt) if math.isfinite(dt) else math.nan)

            push_window(strength_t, strength_v, ts, strength, history_sec)
            push_window(power_t, power_v, ts, power, history_sec)
            push_window(speed_t, speed_v, ts, spd, history_sec)

            img_pose = pose_panel.render(pts17, valid17)
            img_strength = strength_panel.render(strength_t, strength_v)
            img_power = power_panel.render(power_t, power_v)

            canvas = compose_three_panel(img_pose, img_strength, img_power, win_w, win_h, left_w)

            frame_id = fr.get("frame_idx", idx)
            n_valid = int(np.sum(valid21))

            cur_strength = strength_v[-1] if len(strength_v) else math.nan
            cur_power = power_v[-1] if len(power_v) else math.nan
            cur_spd = speed_v[-1] if len(speed_v) else math.nan

            cv2.putText(
                canvas,
                f"frame {frame_id}  valid_pts {n_valid}/21  strength {cur_strength:.3f}  power {cur_power:.3f}  wrist_speed {cur_spd:.3f} m/s  conf_th {conf_th:.2f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (235, 235, 235),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow(win, canvas)

            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord("q"):
                break
            if key == ord(" "):
                paused = not paused
            if key == ord("a"):
                idx = max(0, idx - 1)
                paused = True
            if key == ord("d"):
                idx = min(len(frames) - 1, idx + 1)
                paused = True

            if not paused:
                if not no_sleep:
                    if use_timestamp and idx > 0:
                        dt_play = max(0.0, (t_s[idx] - t_s[idx - 1]) / scale)
                    else:
                        dt_play = 1.0 / max(1e-6, target_fps)

                    now_wall = time.time()
                    spent = now_wall - last_wall
                    sleep_s = dt_play - spent
                    if sleep_s > 0:
                        time.sleep(min(0.2, sleep_s))
                    last_wall = time.time()

                # update prev for speed
                pts21_prev = pts21.copy()
                valid21_prev = valid21.copy()
                idx += 1
            else:
                last_wall = time.time()

    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        pose_panel.close()


if __name__ == "__main__":
    args = parse_args()
    cfg = load_and_merge_config(args.config, args)
    main(cfg)
