#!/usr/bin/env python3

import json
import math
import time
import os
import argparse
from collections import deque
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import cv2

from pose_sensor_fusion.utils.config_loader import load_yaml_config
from pose_sensor_fusion.sync.panel.ui_primitives import to_float, make_panel
from pose_sensor_fusion.sync.panel.panel_timeseries import TimeseriesPanel
from pose_sensor_fusion.sync.panel.layout_3_panel import compose_three_panel

# 21 edges는 여기서 가져옴 (너가 프로젝트에서 이미 쓰는 정의)
# visualize_pose.py 안에 KPT_EDGES(21) 가 있어야 함
from pose_sensor_fusion.vision_utills.visualize.visualize_pose import KPT_EDGES


# JSON 템플릿 구조에서 관절이 들어있는 위치 (저장 구조 기준)
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

# right_wrist index in 21
R_WRIST_21 = 10


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pose_sensor_fusion/visualize_replay.yaml")
    ap.add_argument("--input", default=None, help="Path to .ndjson or .json")
    ap.add_argument("--start_idx", type=int, default=None)
    ap.add_argument("--end_idx", type=int, default=None)
    ap.add_argument("--conf_th", type=float, default=None)
    ap.add_argument("--target_fps", type=float, default=None)
    ap.add_argument("--use_timestamp", action="store_true")
    ap.add_argument("--no_sleep", action="store_true")
    return ap.parse_args()


def load_and_merge_config(config_path: str, args) -> Dict[str, Any]:
    cfg: Dict[str, Any] = load_yaml_config(config_path)

    # input path
    if args.input is not None:
        cfg.setdefault("input", {})
        cfg["input"]["path"] = args.input
    else:
        # compat: if old key exists
        if "input" not in cfg:
            cfg["input"] = {}
        if not cfg["input"].get("path"):
            nd = (cfg.get("ndjson", {}) or {}).get("path")
            if nd:
                cfg["input"]["path"] = nd

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


def load_frames(path: str) -> List[Dict[str, Any]]:
    if not path:
        raise RuntimeError("input.path is empty, use --input or set input.path in config")

    if path.endswith(".ndjson"):
        frames: List[Dict[str, Any]] = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                frames.append(json.loads(line))
        return frames

    with open(path, "r") as f:
        obj = json.load(f)

    if isinstance(obj, dict) and "frames" in obj:
        return list(obj["frames"])
    if isinstance(obj, list):
        return obj

    raise RuntimeError("Unsupported json format, expected {'frames':[...]} or list or .ndjson")


def cam_xyz_to_view(xyz_cam_m) -> np.ndarray:
    x, y, z = float(xyz_cam_m[0]), float(xyz_cam_m[1]), float(xyz_cam_m[2])
    return np.array([x, -y, z], dtype=np.float32)


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


def wrist_speed_mps(
    pts21: np.ndarray,
    valid21: np.ndarray,
    pts21_prev: Optional[np.ndarray],
    valid21_prev: Optional[np.ndarray],
    dt: float,
) -> float:
    if pts21_prev is None or valid21_prev is None:
        return math.nan
    if not math.isfinite(dt) or dt <= 1e-6:
        return math.nan

    if not bool(valid21[R_WRIST_21]) or not bool(valid21_prev[R_WRIST_21]):
        return math.nan

    p0 = pts21_prev[R_WRIST_21]
    p1 = pts21[R_WRIST_21]
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


def render_pose_panel_xy(w: int, h: int, pts21: np.ndarray, valid21: np.ndarray) -> np.ndarray:
    img = make_panel(w, h, bg=12)

    vv = pts21[valid21]
    if vv.shape[0] == 0:
        cv2.putText(img, "no valid points", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (220, 220, 220), 2, cv2.LINE_AA)
        return img

    # 정면 뷰: X-Y 사용 (cam_xyz_to_view에서 y를 이미 -y로 바꿔줌)
    x = vv[:, 0]
    y = vv[:, 1]

    x_min, x_max = float(np.min(x)), float(np.max(x))
    y_min, y_max = float(np.min(y)), float(np.max(y))

    if abs(x_max - x_min) < 1e-3:
        x_min -= 0.5
        x_max += 0.5
    if abs(y_max - y_min) < 1e-3:
        y_min -= 0.5
        y_max += 0.5

    pad = 40

    def proj(p):
        px, py = float(p[0]), float(p[1])
        u = pad + (px - x_min) / (x_max - x_min) * (w - 2 * pad)
        # 화면 y축은 아래로 증가하니까 위아래 뒤집어 주는 게 더 자연스러움
        v = pad + (y_max - py) / (y_max - y_min) * (h - 2 * pad)
        return int(round(u)), int(round(v))

    for a, b in KPT_EDGES:
        if a >= 21 or b >= 21:
            continue
        if valid21[a] and valid21[b]:
            ua, va = proj(pts21[a])
            ub, vb = proj(pts21[b])
            cv2.line(img, (ua, va), (ub, vb), (60, 220, 80), 2)

    for i in range(21):
        if not valid21[i]:
            continue
        u, v = proj(pts21[i])
        cv2.circle(img, (u, v), 4, (50, 80, 240), -1)

    cv2.putText(img, "pose view: X-Y", (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (210, 210, 210), 2, cv2.LINE_AA)
    return img

def render_pose_panel_backview(w: int, h: int, pts21: np.ndarray, valid21: np.ndarray) -> np.ndarray:
    """
    뒤에서 보는 느낌:
    - 화면 좌표: X(가로), Y(세로)
    - Z는 원근 스케일(멀면 작게)로만 사용
    - 프레임마다 min/max로 튀는 거 방지: 고정 범위 사용
    """
    img = make_panel(w, h, bg=12)

    vv = pts21[valid21]
    if vv.shape[0] == 0:
        cv2.putText(img, "no valid points", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (220, 220, 220), 2, cv2.LINE_AA)
        return img

    # 고정 범위(카메라 좌표계 기준, 필요하면 조절)
    # x: 좌우 1.2m, y: 상하 1.2m 정도로 시작
    x_min, x_max = -1.2, 1.2
    y_min, y_max = -1.2, 1.2

    # 원근: z(깊이)가 커질수록 축소
    # z0는 기준 거리, z_gain은 원근 강도
    z0 = 2.0
    z_gain = 1.0

    pad = 40
    cx = w * 0.5
    cy = h * 0.55  # 사람을 화면 중앙보다 살짝 아래에 두면 보기 좋음

    def proj(p):
        px, py, pz = float(p[0]), float(p[1]), float(p[2])

        # y는 화면 좌표계 반전(위가 +가 되도록)
        py = py

        # 원근 스케일
        s = z0 / max(0.3, (pz * z_gain + z0))

        # 정규화 좌표를 화면 픽셀로
        nx = (px - x_min) / (x_max - x_min) - 0.5
        ny = (py - y_min) / (y_max - y_min) - 0.5

        u = cx + nx * (w - 2 * pad) * s
        v = cy - ny * (h - 2 * pad) * s
        return int(round(u)), int(round(v)), s

    # edges
    for a, b in KPT_EDGES:
        if a >= 21 or b >= 21:
            continue
        if valid21[a] and valid21[b]:
            ua, va, sa = proj(pts21[a])
            ub, vb, sb = proj(pts21[b])
            # 가까우면 두껍게
            lw = int(max(1, min(5, round(2.0 * (sa + sb)))))
            cv2.line(img, (ua, va), (ub, vb), (60, 220, 80), lw)

    # points
    for i in range(21):
        if not valid21[i]:
            continue
        u, v, s = proj(pts21[i])
        r = int(max(2, min(8, round(4.0 * s))))
        cv2.circle(img, (u, v), r, (50, 80, 240), -1)

    cv2.putText(img, "pose view: back (X,Y + perspective by Z)", (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (210, 210, 210), 2, cv2.LINE_AA)
    return img


def main(cfg: Dict[str, Any]) -> None:
    input_path = (cfg.get("input", {}) or {}).get("path")
    if not input_path:
        raise RuntimeError("input.path is empty, use --input or set in config")

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

    frames = load_frames(input_path)
    if not frames:
        raise RuntimeError("input empty")

    s = max(0, start_idx)
    e = end_idx if end_idx >= 0 else len(frames)
    if s >= len(frames):
        raise RuntimeError(f"start_idx {s} >= total frames {len(frames)}")
    frames = frames[s:e]

    t_s: List[float] = []
    for i, fr in enumerate(frames):
        t_s.append(get_ts_seconds(fr, fallback_s=float(i) / max(1e-6, target_fps)))

    dt_src = [max(1e-6, t_s[i] - t_s[i - 1]) for i in range(1, len(t_s))]
    median_dt = float(np.median(np.array(dt_src, dtype=np.float64))) if dt_src else (1.0 / target_fps)
    dt_tgt = 1.0 / max(1e-6, target_fps)
    # scale = max(1e-6, median_dt / dt_tgt)
    scale = 1.0

    strength_t = deque()
    strength_v = deque()
    power_t = deque()
    power_v = deque()

    speed_t = deque()
    speed_v = deque()

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

    win = "Pose(XZ) + strength/power (q,esc quit, space pause, a,d step)"
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

            strength = get_strength(fr)
            power = get_power(fr)

            dt = (t_s[idx] - t_s[idx - 1]) if idx > 0 else math.nan
            spd = wrist_speed_mps(pts21, valid21, pts21_prev, valid21_prev, float(dt))

            push_window(strength_t, strength_v, ts, strength, history_sec)
            push_window(power_t, power_v, ts, power, history_sec)
            push_window(speed_t, speed_v, ts, spd, history_sec)

            img_pose = render_pose_panel_backview(o3d_w, o3d_h, pts21, valid21)
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
                        # time.sleep(min(0.2, sleep_s))
                        time.sleep(sleep_s)
                    last_wall = time.time()

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


if __name__ == "__main__":
    os.environ["DISPLAY"] = ":0"

    args = parse_args()
    cfg = load_and_merge_config(args.config, args)
    main(cfg)
