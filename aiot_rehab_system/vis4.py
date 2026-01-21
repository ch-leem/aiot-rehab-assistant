#!/usr/bin/env python3
# visualize_full17_pretty_v3_2plots.py

import csv
import math
import time
import argparse
from collections import deque

import numpy as np
import cv2
import open3d as o3d


COCO_EDGES = [
    (5, 7), (7, 9),
    (6, 8), (8, 10),
    (5, 6),
    (5, 11), (6, 12),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (0, 1), (0, 2), (1, 3), (2, 4),
]


def _to_float(x):
    if x is None:
        return math.nan
    s = str(x).strip()
    if s == "" or s.lower() in ("nan", "none", "null"):
        return math.nan
    try:
        return float(s)
    except Exception:
        return math.nan


def load_rows(path):
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        return [row for row in r]


def make_panel(w, h, bg=16):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (bg, bg, bg)
    return img


def draw_card(img, x0, y0, x1, y1, radius=18, color=(28, 28, 28), border=(55, 55, 55)):
    cv2.rectangle(img, (x0 + radius, y0), (x1 - radius, y1), color, -1)
    cv2.rectangle(img, (x0, y0 + radius), (x1, y1 - radius), color, -1)
    cv2.circle(img, (x0 + radius, y0 + radius), radius, color, -1)
    cv2.circle(img, (x1 - radius, y0 + radius), radius, color, -1)
    cv2.circle(img, (x0 + radius, y1 - radius), radius, color, -1)
    cv2.circle(img, (x1 - radius, y1 - radius), radius, color, -1)
    cv2.rectangle(img, (x0, y0), (x1, y1), border, 1)


def plot_timeseries(img, ts_s, ys, title, y_label, color_line, y_min=None, y_max=None):
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
        cv2.polylines(img, [np.array(pts, dtype=np.int32)], False, color_line, 2, cv2.LINE_AA)

    cv2.putText(img, title, (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (235, 235, 235), 2, cv2.LINE_AA)
    cv2.putText(img, y_label, (18, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (180, 180, 180), 2, cv2.LINE_AA)
    cv2.putText(img, f"{y_max:.2f}", (12, y0 + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA)
    cv2.putText(img, f"{y_min:.2f}", (12, y1 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA)


def cam_xyz_to_view(xyz_cam_m):
    x, y, z = float(xyz_cam_m[0]), float(xyz_cam_m[1]), float(xyz_cam_m[2])
    return np.array([x, -y, z], dtype=np.float32)


def parse_joints17(row, conf_th=0.0):
    pts = np.full((17, 3), np.nan, dtype=np.float32)
    valid = np.zeros((17,), dtype=bool)
    conf = np.full((17,), np.nan, dtype=np.float32)

    has_kp = (row.get("kp0_x") is not None) or (row.get("kp0_u") is not None)
    for j in range(17):
        if has_kp:
            x = _to_float(row.get(f"kp{j}_x"))
            y = _to_float(row.get(f"kp{j}_y"))
            z = _to_float(row.get(f"kp{j}_z"))
            c = _to_float(row.get(f"kp{j}_s"))
            if not math.isfinite(c):
                c = _to_float(row.get(f"kp{j}_conf"))
        else:
            x = _to_float(row.get(f"j{j}_x_m"))
            y = _to_float(row.get(f"j{j}_y_m"))
            z = _to_float(row.get(f"j{j}_z_m"))
            c = _to_float(row.get(f"j{j}_conf"))

        conf[j] = c
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z) and math.isfinite(c) and c >= conf_th:
            pts[j] = cam_xyz_to_view((x, y, z))
            valid[j] = True

    return pts, valid, conf


def elbow_angvel_degps(row, t_s, last):
    ang = _to_float(row.get("r_elbow_deg"))
    if not math.isfinite(ang):
        ang = _to_float(row.get("l_elbow_deg"))

    if not math.isfinite(ang):
        return math.nan, last

    if last is None:
        return math.nan, (ang, t_s)

    last_ang, last_t = last
    dt = max(t_s - last_t, 1e-6)
    w = (ang - last_ang) / dt
    return float(w), (ang, t_s)


def build_lineset_compact(points17_finite, valid17):
    raw_lines = []
    used = set()
    for a, b in COCO_EDGES:
        if valid17[a] and valid17[b]:
            raw_lines.append((a, b))
            used.add(a)
            used.add(b)

    if len(raw_lines) == 0 or len(used) < 2:
        return None

    used = sorted(list(used))
    idx_map = {old: new for new, old in enumerate(used)}

    pts_compact = points17_finite[used].astype(np.float64)
    lines_compact = np.array([(idx_map[a], idx_map[b]) for a, b in raw_lines], dtype=np.int32)

    if pts_compact.shape[0] == 0 or lines_compact.shape[0] == 0:
        return None

    ls = o3d.geometry.LineSet()
    ls.points = o3d.utility.Vector3dVector(pts_compact)
    ls.lines = o3d.utility.Vector2iVector(lines_compact)
    colors = np.tile(np.array([[0.18, 0.92, 0.28]], dtype=np.float64), (lines_compact.shape[0], 1))
    ls.colors = o3d.utility.Vector3dVector(colors)
    return ls


def robust_camera_from_points(points17, valid17):
    vv = points17[valid17]
    if vv.shape[0] >= 3:
        center = vv.mean(axis=0)
        mn = vv.min(axis=0)
        mx = vv.max(axis=0)
        extent = mx - mn
        diag = float(np.linalg.norm(extent))
        diag = max(diag, 0.5)
    elif vv.shape[0] > 0:
        center = vv.mean(axis=0)
        diag = 1.2
    else:
        center = np.array([0.0, 0.0, 2.0], dtype=np.float32)
        diag = 1.5

    dist = float(np.clip(diag * 2.5, 1.5, 8.0))
    eye = center + np.array([0.0, 0.0, -dist], dtype=np.float32)
    up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    near = 0.01
    far = 50.0
    return eye, center, up, near, far


def try_offscreen_renderer(w, h):
    try:
        from open3d.visualization import rendering
        r = rendering.OffscreenRenderer(w, h)
        return r
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="/home/a203/workspace/S14P11A203/tmp2/logs/pose_imu_20260121_150226.csv")
    ap.add_argument("--start_idx", type=int, default=400)
    ap.add_argument("--end_idx", type=int, default=-1)
    ap.add_argument("--conf_th", type=float, default=0.1)
    ap.add_argument("--history_sec", type=float, default=6.0)
    ap.add_argument("--target_fps", type=float, default=25.0)
    ap.add_argument("--use_timestamp", action="store_true")
    ap.add_argument("--no_sleep", action="store_true")
    ap.add_argument("--o3d_w", type=int, default=900)
    ap.add_argument("--o3d_h", type=int, default=800)

    ap.add_argument("--imu_ymin", type=float, default=0.0)
    ap.add_argument("--imu_ymax", type=float, default=200.0)
    ap.add_argument("--vis_ymin", type=float, default=0.0)
    ap.add_argument("--vis_ymax", type=float, default=200.0)

    args = ap.parse_args()

    rows = load_rows(args.csv)
    if not rows:
        raise RuntimeError("csv empty")

    start = max(0, args.start_idx)
    end = args.end_idx if args.end_idx >= 0 else len(rows)
    if start >= len(rows):
        raise RuntimeError(f"start_idx {start} >= total rows {len(rows)}")
    rows = rows[start:end]

    t_ms = [_to_float(r.get("host_ts_ms")) for r in rows]
    t_ms = [x if math.isfinite(x) else _to_float(r.get("video_ts_ms")) for x, r in zip(t_ms, rows)]
    t_s = [float(x) / 1000.0 for x in t_ms]

    dt_src = []
    for i in range(1, len(t_s)):
        dt_src.append(max(1e-6, t_s[i] - t_s[i - 1]))
    median_dt = float(np.median(np.array(dt_src, dtype=np.float64))) if dt_src else (1.0 / args.target_fps)
    dt_tgt = 1.0 / max(1e-6, args.target_fps)
    scale = max(1e-6, median_dt / dt_tgt)

    imu_t = deque(); imu_v = deque()
    vis_t = deque(); vis_w = deque()

    last_angle_state = None

    def push_window(t_deque, y_deque, t_now, y_now, window_sec):
        t_deque.append(t_now)
        y_deque.append(y_now)
        t_min = t_now - window_sec
        while len(t_deque) > 0 and t_deque[0] < t_min:
            t_deque.popleft()
            y_deque.popleft()

    renderer = try_offscreen_renderer(args.o3d_w, args.o3d_h)

    win = "3D + 2 Signals (q,esc quit, space pause, a,d step)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 1600, 900)

    paused = False
    idx = 0
    last_wall = time.time()

    try:
        while True:
            if idx >= len(rows):
                paused = True
                idx = len(rows) - 1

            r = rows[idx]
            ts = t_s[idx]

            imu_val = _to_float(r.get("imu_v_cmps"))
            w_vis, last_angle_state = elbow_angvel_degps(r, ts, last_angle_state)

            push_window(imu_t, imu_v, ts, imu_val, args.history_sec)
            push_window(vis_t, vis_w, ts, w_vis, args.history_sec)

            pts17, valid17, conf17 = parse_joints17(r, conf_th=args.conf_th)

            # --- 3D render (v3 스타일) ---
            if renderer is not None:
                from open3d.visualization import rendering

                scene = renderer.scene
                scene.clear_geometry()
                scene.set_background([0.08, 0.08, 0.09, 1.0])

                vv_valid = pts17[valid17]
                if vv_valid.shape[0] > 0:
                    pcd = o3d.geometry.PointCloud()
                    pcd.points = o3d.utility.Vector3dVector(vv_valid.astype(np.float64))
                    mat_pts = rendering.MaterialRecord()
                    mat_pts.shader = "defaultUnlit"
                    mat_pts.point_size = 12.0
                    mat_pts.base_color = (0.95, 0.25, 0.25, 1.0)
                    scene.add_geometry("pts", pcd, mat_pts)

                vv = pts17.copy()
                vv[np.isnan(vv)] = 0.0
                ls = build_lineset_compact(vv, valid17)
                if ls is not None:
                    mat_ls = rendering.MaterialRecord()
                    mat_ls.shader = "defaultUnlit"
                    mat_ls.line_width = 5.0
                    scene.add_geometry("ls", ls, mat_ls)

                eye, center, up, near, far = robust_camera_from_points(pts17, valid17)
                aspect = float(args.o3d_w) / float(args.o3d_h)
                scene.camera.set_projection(60.0, aspect, near, far, rendering.Camera.FovType.Vertical)
                scene.camera.look_at(center.astype(np.float64), eye.astype(np.float64), up.astype(np.float64))

                img_o3d = renderer.render_to_image()
                img_np = np.asarray(img_o3d)
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            else:
                img_np = make_panel(args.o3d_w, args.o3d_h, bg=12)
                cv2.putText(img_np, "OffscreenRenderer not available",
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (220, 220, 220), 2, cv2.LINE_AA)

            # --- UI compose (left:3D, right: 2 plots) ---
            H, W = 900, 1600
            canvas = make_panel(W, H, bg=16)

            left_w = 980
            left = canvas[:, :left_w]
            right = canvas[:, left_w:]

            slot_w = left_w - 40
            slot_h = H - 40
            im = cv2.resize(img_np, (slot_w, slot_h), interpolation=cv2.INTER_AREA)

            draw_card(left, 10, 10, left_w - 10, H - 10, radius=18)
            left[20:H - 20, 20:left_w - 20] = im

            top = right[:H // 2, :]
            bot = right[H // 2:, :]

            plot_timeseries(top, list(imu_t), list(imu_v),
                            title="IMU value (imu_v_cmps)", y_label="cm/s",
                            color_line=(80, 210, 255),
                            y_min=args.imu_ymin, y_max=args.imu_ymax)

            plot_timeseries(bot, list(vis_t), list(vis_w),
                            title="Vision angular velocity (from elbow angle)", y_label="deg/s",
                            color_line=(255, 170, 90),
                            y_min=args.vis_ymin, y_max=args.vis_ymax)

            cur_frame = r.get("frame_idx", str(idx))
            cur_imu = imu_v[-1] if len(imu_v) else math.nan
            cur_w = vis_w[-1] if len(vis_w) else math.nan
            n_valid = int(np.sum(valid17))

            cv2.putText(
                canvas,
                f"frame {cur_frame}  valid_pts {n_valid}/17  imu {cur_imu:.3f} cm/s  vision_angvel {cur_w:.3f} deg/s  conf_th {args.conf_th:.2f}",
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
                if not args.no_sleep:
                    if args.use_timestamp and idx > 0:
                        dt_play = max(0.0, (t_s[idx] - t_s[idx - 1]) / scale)
                    else:
                        dt_play = 1.0 / max(1e-6, args.target_fps)

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
        try:
            if renderer is not None:
                renderer.release()
        except Exception:
            pass


if __name__ == "__main__":
    main()
