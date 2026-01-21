#!/usr/bin/env python3

import csv
import math
import time
import argparse
from collections import deque
from typing import Dict, Any, List, Tuple

import numpy as np
import cv2

from pose_sensor_fusion.utils.config_loader import load_yaml_config
from pose_sensor_fusion.sync.panel.ui_primitives import to_float
from pose_sensor_fusion.sync.panel.panel_pose3d import Pose3DPanel, cam_xyz_to_view
from pose_sensor_fusion.sync.panel.panel_timeseries import TimeseriesPanel
from pose_sensor_fusion.sync.panel.layout_3_panel import compose_three_panel

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pose_sensor_fusion/visualize_replay.yaml")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--start_idx", type=int, default=None)
    ap.add_argument("--end_idx", type=int, default=None)
    ap.add_argument("--conf_th", type=float, default=None)
    ap.add_argument("--target_fps", type=float, default=None)
    ap.add_argument("--use_timestamp", action="store_true")
    ap.add_argument("--no_sleep", action="store_true")
    return ap.parse_args()


def load_and_merge_config(config_path: str, args) -> Dict[str, Any]:
    cfg: Dict[str, Any] = load_yaml_config(config_path)

    if args.csv is not None:
        cfg["csv"]["path"] = args.csv
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

def load_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        return [row for row in r]


def parse_joints17(row: Dict[str, str], conf_th: float = 0.0):
    pts = np.full((17, 3), np.nan, dtype=np.float32)
    valid = np.zeros((17,), dtype=bool)

    has_kp = (row.get("kp0_x") is not None) or (row.get("kp0_u") is not None)

    for j in range(17):
        if has_kp:
            x = to_float(row.get(f"kp{j}_x"))
            y = to_float(row.get(f"kp{j}_y"))
            z = to_float(row.get(f"kp{j}_z"))
            c = to_float(row.get(f"kp{j}_s"))
            if not math.isfinite(c):
                c = to_float(row.get(f"kp{j}_conf"))
        else:
            x = to_float(row.get(f"j{j}_x_m"))
            y = to_float(row.get(f"j{j}_y_m"))
            z = to_float(row.get(f"j{j}_z_m"))
            c = to_float(row.get(f"j{j}_conf"))

        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z) and math.isfinite(c) and c >= conf_th:
            pts[j] = cam_xyz_to_view((x, y, z))
            valid[j] = True

    return pts, valid


def elbow_angvel_degps(row: Dict[str, str], t_s: float, last):
    ang = to_float(row.get("r_elbow_deg"))
    if not math.isfinite(ang):
        ang = to_float(row.get("l_elbow_deg"))

    if not math.isfinite(ang):
        return math.nan, last

    if last is None:
        return math.nan, (ang, t_s)

    last_ang, last_t = last
    dt = max(t_s - last_t, 1e-6)
    w = (ang - last_ang) / dt
    return float(w), (ang, t_s)


def push_window(t_deque: deque, y_deque: deque, t_now: float, y_now: float, window_sec: float) -> None:
    t_deque.append(t_now)
    y_deque.append(y_now)
    t_min = t_now - window_sec
    while len(t_deque) > 0 and t_deque[0] < t_min:
        t_deque.popleft()
        y_deque.popleft()


def main(cfg: Dict[str, Any]) -> None:
    csv_path = cfg["csv"]["path"]

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

    imu_cfg = cfg["plot"]["imu"]
    vis_cfg = cfg["plot"]["vision"]

    rows = load_rows(csv_path)
    if not rows:
        raise RuntimeError("csv empty")

    s = max(0, start_idx)
    e = end_idx if end_idx >= 0 else len(rows)
    if s >= len(rows):
        raise RuntimeError(f"start_idx {s} >= total rows {len(rows)}")
    rows = rows[s:e]

    t_ms = [to_float(r.get("host_ts_ms")) for r in rows]
    t_ms = [x if math.isfinite(x) else to_float(r.get("video_ts_ms")) for x, r in zip(t_ms, rows)]
    t_s = [float(x) / 1000.0 for x in t_ms]

    dt_src = [max(1e-6, t_s[i] - t_s[i - 1]) for i in range(1, len(t_s))]
    median_dt = float(np.median(np.array(dt_src, dtype=np.float64))) if dt_src else (1.0 / target_fps)
    dt_tgt = 1.0 / max(1e-6, target_fps)
    scale = max(1e-6, median_dt / dt_tgt)

    imu_t = deque()
    imu_v = deque()
    vis_t = deque()
    vis_w = deque()

    pose_panel = Pose3DPanel(o3d_w, o3d_h)

    right_w = win_w - left_w
    plot_h = win_h // 2
    imu_panel = TimeseriesPanel(
        right_w,
        plot_h,
        title=str(imu_cfg["title"]),
        y_label=str(imu_cfg["y_label"]),
        y_min=float(imu_cfg["y_min"]),
        y_max=float(imu_cfg["y_max"]),
        color_bgr=tuple(imu_cfg["color_bgr"]),
    )
    vis_panel = TimeseriesPanel(
        right_w,
        win_h - plot_h,
        title=str(vis_cfg["title"]),
        y_label=str(vis_cfg["y_label"]),
        y_min=float(vis_cfg["y_min"]),
        y_max=float(vis_cfg["y_max"]),
        color_bgr=tuple(vis_cfg["color_bgr"]),
    )

    win = "3D + 2 Signals (q,esc quit, space pause, a,d step)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, win_w, win_h)

    paused = False
    idx = 0
    last_wall = time.time()
    last_angle_state = None

    try:
        while True:
            if idx >= len(rows):
                paused = True
                idx = len(rows) - 1

            r = rows[idx]
            ts = t_s[idx]

            imu_val = to_float(r.get("imu_v_cmps"))
            w_vis, last_angle_state = elbow_angvel_degps(r, ts, last_angle_state)

            push_window(imu_t, imu_v, ts, imu_val, history_sec)
            push_window(vis_t, vis_w, ts, w_vis, history_sec)

            pts17, valid17 = parse_joints17(r, conf_th=conf_th)

            img_pose = pose_panel.render(pts17, valid17)
            img_imu = imu_panel.render(imu_t, imu_v)
            img_vis = vis_panel.render(vis_t, vis_w)

            canvas = compose_three_panel(img_pose, img_imu, img_vis, win_w, win_h, left_w)

            cur_frame = r.get("frame_idx", str(idx))
            n_valid = int(np.sum(valid17))
            cur_imu = imu_v[-1] if len(imu_v) else math.nan
            cur_w = vis_w[-1] if len(vis_w) else math.nan

            cv2.putText(
                canvas,
                f"frame {cur_frame}  valid_pts {n_valid}/17  imu {cur_imu:.3f} cm/s  vision_angvel {cur_w:.3f} deg/s  conf_th {conf_th:.2f}",
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
                idx = min(len(rows) - 1, idx + 1)
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
