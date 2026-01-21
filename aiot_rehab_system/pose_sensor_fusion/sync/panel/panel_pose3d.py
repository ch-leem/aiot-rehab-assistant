from typing import Optional, Tuple
import numpy as np
import cv2
import open3d as o3d

from .ui_primitives import make_panel
from pose_sensor_fusion.vision_utills.visualize.visualize_pose import KPT_EDGES


def cam_xyz_to_view(xyz_cam_m) -> np.ndarray:
    x, y, z = float(xyz_cam_m[0]), float(xyz_cam_m[1]), float(xyz_cam_m[2])
    return np.array([x, -y, z], dtype=np.float32)


def build_lineset_compact(points_finite: np.ndarray, valid: np.ndarray) -> Optional[o3d.geometry.LineSet]:
    raw_lines = []
    used = set()

    for a, b in KPT_EDGES:
        if valid[a] and valid[b]:
            raw_lines.append((a, b))
            used.add(a)
            used.add(b)

    if len(raw_lines) == 0 or len(used) < 2:
        return None

    used = sorted(list(used))
    idx_map = {old: new for new, old in enumerate(used)}

    pts_compact = points_finite[used].astype(np.float64)
    lines_compact = np.array([(idx_map[a], idx_map[b]) for a, b in raw_lines], dtype=np.int32)

    if pts_compact.shape[0] == 0 or lines_compact.shape[0] == 0:
        return None

    ls = o3d.geometry.LineSet()
    ls.points = o3d.utility.Vector3dVector(pts_compact)
    ls.lines = o3d.utility.Vector2iVector(lines_compact)

    colors = np.tile(np.array([[0.18, 0.92, 0.28]], dtype=np.float64), (lines_compact.shape[0], 1))
    ls.colors = o3d.utility.Vector3dVector(colors)
    return ls


def robust_camera_from_points(points: np.ndarray, valid: np.ndarray):
    vv = points[valid]
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


def try_offscreen_renderer(w: int, h: int):
    try:
        from open3d.visualization import rendering
        r = rendering.OffscreenRenderer(w, h)
        return r
    except Exception:
        return None


class Pose3DPanel:
    def __init__(self, w: int, h: int):
        self.w = int(w)
        self.h = int(h)
        self.renderer = try_offscreen_renderer(self.w, self.h)

    def close(self) -> None:
        try:
            if self.renderer is not None:
                self.renderer.release()
        except Exception:
            pass
        self.renderer = None

    def render(self, pts: np.ndarray, valid: np.ndarray) -> np.ndarray:
        if self.renderer is None:
            img = make_panel(self.w, self.h, bg=12)
            cv2.putText(
                img,
                "OffscreenRenderer not available",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (220, 220, 220),
                2,
                cv2.LINE_AA,
            )
            return img

        from open3d.visualization import rendering

        scene = self.renderer.scene
        scene.clear_geometry()
        scene.set_background([0.08, 0.08, 0.09, 1.0])

        vv_valid = pts[valid]
        if vv_valid.shape[0] > 0:
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(vv_valid.astype(np.float64))
            mat_pts = rendering.MaterialRecord()
            mat_pts.shader = "defaultUnlit"
            mat_pts.point_size = 12.0
            mat_pts.base_color = (0.95, 0.25, 0.25, 1.0)
            scene.add_geometry("pts", pcd, mat_pts)

        vv = pts.copy()
        vv[np.isnan(vv)] = 0.0
        ls = build_lineset_compact(vv, valid)
        if ls is not None:
            mat_ls = rendering.MaterialRecord()
            mat_ls.shader = "defaultUnlit"
            mat_ls.line_width = 5.0
            scene.add_geometry("ls", ls, mat_ls)

        eye, center, up, near, far = robust_camera_from_points(pts, valid)
        aspect = float(self.w) / float(self.h)
        scene.camera.set_projection(60.0, aspect, near, far, rendering.Camera.FovType.Vertical)
        scene.camera.look_at(center.astype(np.float64), eye.astype(np.float64), up.astype(np.float64))

        img_o3d = self.renderer.render_to_image()
        img_np = np.asarray(img_o3d)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        return img_np
