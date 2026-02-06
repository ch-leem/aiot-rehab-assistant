#!/usr/bin/env python3

import os
import time
import math
from typing import Dict, Optional, Tuple, List, Any

import cv2
import numpy as np

from pose_sensor_fusion.imu.imu_udp_buffer import ImuUdpBuffer
from pose_sensor_fusion.load_cell.load_cell_udp_buffer import WeightUdpBuffer


from pose_sensor_fusion.vision_utills.realsense_ai_api import RealSenseAIApi, FrameBundle
from pose_sensor_fusion.vision_utills.inference.trt_engine import TrtEngine
from pose_sensor_fusion.vision_utills.pose3d.pose_filter import OneEuroFilter3D
from pose_sensor_fusion.vision_utills.preprocess.img_preprocessing import preprocess_bgr_letterbox, unletterbox_points
from pose_sensor_fusion.vision_utills.pose2d.pose_2d_postprocessing import decode_pose, pick_person, TrackState
from pose_sensor_fusion.vision_utills.pose3d.depth_lift import robust_depth_at
from pose_sensor_fusion.vision_utills.visualize.visualize_pose import (
    draw_pose_2d,
    angle_3pts,
    KPT,
    Joint3DState,
)

from pose_sensor_fusion.utils.config_loader import load_yaml_config
from pose_sensor_fusion.utils.create_payload import load_data_payload, build_frame_from_pose
from pose_sensor_fusion.utils.json_logger import JsonLogger


def fmt_deg(v: float) -> str:
    return "nan" if (v is None or not np.isfinite(v)) else f"{v:6.1f}"

def put_lines(img, x: int, y: int, lines, scale=0.6, thickness=2, line_gap=22):
    for i, s in enumerate(lines):
        cv2.putText(
            img,
            s,
            (x, y + i * line_gap),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (0, 255, 255),
            thickness,
        )

# 관절 위치가 유효한 값인지 체크 -> 유효한 값이면 각도 계산
def _finite_xyz(xyz: Optional[np.ndarray]) -> bool:
    if xyz is None:
        return False
    return bool(np.isfinite(xyz).all())

# 각도 계산 함수
def angle_3pts(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:

    if not _finite_xyz(a) or not _finite_xyz(b) or not _finite_xyz(c):
        return float("nan")

    ba = a - b
    bc = c - b
    nba = float(np.linalg.norm(ba))
    nbc = float(np.linalg.norm(bc))
    if nba < 1e-6 or nbc < 1e-6:
        return float("nan")
    cosang = float(np.dot(ba, bc) / (nba * nbc))
    cosang = max(-1.0, min(1.0, cosang))
    return math.degrees(math.acos(cosang))

# 기울기 계산 함수
def slope_xy(p1: np.ndarray, p2: np.ndarray, eps: float = 1e-6) -> float:
    """
    수평 기울기
    XY 평면에서 p1 -> p2 벡터의 각도
    기준: +X 축, 반시계 방향이 +
    """
    if not _finite_xyz(p1) or not _finite_xyz(p2):
        return float("nan")

    d = p2 - p1
    dx = float(d[0])
    dy = float(d[1])

    if abs(dx) < eps and abs(dy) < eps:
        return float("nan")

    return math.degrees(math.atan2(dy, dx))

# 센터 좌표 계산 함수
def center(p1, p2):
    if _finite_xyz(p1) and _finite_xyz(p2):
        return 0.5 * (p1 + p2)
    return float("nan")

def slope_yz(p1: np.ndarray, p2: np.ndarray, eps: float = 1e-6) -> float:
    """
    상체 기울기
    YZ 평면에서 p1 -> p2 벡터의 각도
    기준: +Y 축, +Z 방향이 +
    """
    if not _finite_xyz(p1) or not _finite_xyz(p2):
        return float("nan")

    d = p2 - p1
    dy = float(d[1])
    dz = float(d[2])

    if abs(dy) < eps and abs(dz) < eps:
        return float("nan")

    return math.degrees(math.atan2(dz, dy))

def main(cfg: Dict[str, Any]) -> None:

    # config file parameters
    engine_path = cfg["engine"]["path"]

    conf_th = float(cfg["inference"]["conf_th"])
    iou_th = float(cfg["inference"]["iou_th"])
    kp_th = float(cfg["inference"]["kp_th"])

    hold_sec = float(cfg["tracking"]["hold_sec"])
    stick_iou = float(cfg["tracking"]["stick_iou"])

    depth_roi = int(cfg["depth"]["roi"])
    min_valid_ratio = float(cfg["depth"]["min_valid_ratio"])
    outlier_mad_k = float(cfg["depth"]["outlier_mad_k"])

    filt_min_cutoff = float(cfg["filter"]["min_cutoff"])
    filt_beta = float(cfg["filter"]["beta"])
    filt_d_cutoff = float(cfg["filter"]["d_cutoff"])

    rgb_w = int(cfg["stream"]["rgb"]["width"])
    rgb_h = int(cfg["stream"]["rgb"]["height"])
    fps = int(cfg["stream"]["fps"])

    imu_cfg = cfg["imu"]
    IMU_MATCH = imu_cfg["match"]
    IMU_MAX_ABS_AGE_MS = float(imu_cfg["max_abs_age_ms"])

    lc_cfg = cfg.get("load_cell", {})
    LC_ENABLE = bool(lc_cfg.get("enable", True))
    LC_MATCH = lc_cfg.get("match", "nearest")
    LC_MAX_ABS_AGE_MS = float(lc_cfg.get("max_abs_age_ms", 500.0))

    num_joints = cfg["inference"]["num_joints"]

    imu = ImuUdpBuffer(
        listen_ip=imu_cfg["udp_ip"], 
        listen_port=imu_cfg["udp_port"], 
        max_age_sec=imu_cfg["buffer_sec"]
    )

    imu.start()

    load_cell = WeightUdpBuffer(
        listen_ip=lc_cfg.get("udp_ip", "0.0.0.0"),
        listen_port=int(lc_cfg.get("udp_port", 9998)),
        max_age_sec=float(lc_cfg.get("buffer_sec", 8.0)),
    )

    load_cell.start()

    # 데이터 페이로드 작성
    logger = JsonLogger(cfg["logging"]["output_dir"], prefix="pose21_imu")
    payload_template = load_data_payload(cfg["logging"]["payload_path"])

    print(f"[LOG] NDJSON -> {logger.path}")
    print(f"[IMU] udp :{imu_cfg['udp_port']} match={IMU_MATCH} buffer={imu_cfg['buffer_sec']:.1f}s")
    print(
        f"[LOADCELL] udp :{lc_cfg.get('udp_port', 9998)} "
        f"match={LC_MATCH} buffer={float(lc_cfg.get('buffer_sec', 8.0)):.1f}s"
    )

    trt_engine = TrtEngine(engine_path)

    filters_3d: Dict[int, OneEuroFilter3D] = {
        i: OneEuroFilter3D(filt_min_cutoff, filt_beta, filt_d_cutoff) for i in range(num_joints)
    }
    prev_filt: Dict[int, Tuple[np.ndarray, float]] = {}

    st = TrackState()
    fps_ema = 0.0
    last_frame_t = time.time()
    frame_idx = 0

    win_name = "pose21_strength_power"

    try:
        with RealSenseAIApi(
            rgb_size=(rgb_w, rgb_h),
            depth_size=(rgb_w, rgb_h),
            fps=fps,
            enable_depth=True,
            align_depth_to="color",
            rgb_format="bgr",
            depth_hole_filling=1,
            depth_decimation=1,
            timeout_ms=2000,
        ) as cam:

            intr = cam.rgb_intrinsics()
            depth_scale = cam.depth_scale()
            if depth_scale is None:
                raise RuntimeError("Depth scale is None")

            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_name, 1280, 960)

            while True:
                bundle: FrameBundle = cam.get_frames(want_depth_frame=True, postprocess_depth=False)
                frame = bundle.rgb
                depth_z16 = bundle.depth
                if frame is None or depth_z16 is None:
                    continue

                video_ts_ms = float(bundle.timestamp_ms)
                host_ts_ms = time.time() * 1000.0
                color_ts_ms = bundle.color_timestamp_ms if bundle.color_timestamp_ms is not None else video_ts_ms
                depth_ts_ms = bundle.depth_timestamp_ms
                color_frame_no = bundle.color_frame_number
                depth_frame_no = bundle.depth_frame_number

                # IMU 매칭
                if IMU_MATCH == "interp":
                    imu_s, imu_age_ms, used_interp = imu.match_interp(host_ts_ms)
                else:
                    imu_s, imu_age_ms = imu.match_nearest(host_ts_ms)
                    used_interp = False

                if imu_s is None or abs(imu_age_ms) > IMU_MAX_ABS_AGE_MS:
                    imu_v = float("nan")
                    imu_seq = -1
                    imu_ts = -1
                    imu_age_out = float("inf")
                else:
                    imu_v = float(imu_s.strength_cmps)
                    imu_seq = int(imu_s.seq)
                    imu_ts = int(imu_s.imu_ts_ms)
                    imu_age_out = float(imu_age_ms)

                # Load Cell 매칭
                if load_cell is None:
                    weight_kg = float("nan")
                    weight_seq = -1
                    weight_ts = -1
                    weight_age_out = float("inf")
                    weight_used_interp = False
                else:
                    if LC_MATCH == "interp":
                        w_s, w_age_ms, weight_used_interp = load_cell.match_interp(host_ts_ms)
                    else:
                        w_s, w_age_ms = load_cell.match_nearest(host_ts_ms)
                        weight_used_interp = False

                    if w_s is None or abs(w_age_ms) > LC_MAX_ABS_AGE_MS:
                        weight_kg = float("nan")
                        weight_seq = -1
                        weight_ts = -1
                        weight_age_out = float("inf")
                    else:
                        weight_kg = float(w_s.weight_kg)
                        weight_seq = int(w_s.seq)
                        weight_ts = int(w_s.board_ts_ms)
                        weight_age_out = float(w_age_ms)


                inp, scale, dx, dy = preprocess_bgr_letterbox(frame, 640)
                out_trt = trt_engine.infer(inp)
                infer_done_host_ms = time.time() * 1000.0

                boxes, scores, kpts = decode_pose(out_trt, conf_th=conf_th, iou_th=iou_th)
                pick = pick_person(boxes, scores, kpts, st, stick_iou=stick_iou)

                now = time.time()

                if pick is None:
                    if st.kpts_640 is not None and (now - st.last_seen) <= hold_sec:
                        kpts_640 = st.kpts_640.copy()
                    else:
                        kpts_640 = None
                else:
                    bbox, sc, k_640 = pick
                    st.last_seen = now
                    st.bbox = bbox.copy()
                    st.kpts_640 = k_640.copy()
                    kpts_640 = st.kpts_640.copy()

                disp = frame.copy()

                # 카메라 영상 비활성화
                # disp = np.zeros_like(frame)
                # 오버레이를 disp에 그림
                # alpha = 0.0
                # disp = cv2.addWeighted(frame, alpha, disp, 1.0, 0)
                

                # Outputs to store
                joint_xyz: List[Optional[np.ndarray]] = [None] * num_joints
                joint_conf: List[float] = [None] * num_joints

                r_wspd = float("nan")
                l_wspd = float("nan")
                rw_conf = float("nan")
                lw_conf = float("nan")

                # upper body
                l_shoulder_flex = float("nan")
                r_shoulder_flex = float("nan")

                l_elbow = float("nan")
                r_elbow = float("nan")

                trunk_tilt = float("nan")
                trunk_rot_lat = float("nan")
                pelvis_level = float("nan")

                # lower body
                l_hip_flex = float("nan")
                r_hip_flex = float("nan")

                l_knee_flex = float("nan")
                r_knee_flex = float("nan")

                l_ankle_pf = float("nan")
                r_ankle_pf = float("nan")

                l_ankle_inv_ev = float("nan")
                r_ankle_inv_ev = float("nan")

                l_heel_tilt = float("nan")
                r_heel_tilt = float("nan")
            
                if kpts_640 is not None:
                    kpts_xy = unletterbox_points(kpts_640.reshape(-1, 3), scale, dx, dy)
                    draw_pose_2d(disp, kpts_xy, kp_th=kp_th)

                    joint_states: Dict[int, Joint3DState] = {}

                    for i in range(num_joints):
                        x, y, s = kpts_xy[i]
                        # if i == 3:
                        #     print(f"[joint {i}] s={float(s):.2f}")
                        joint_conf[i] = float(s)

                        if float(s) < kp_th:
                            joint_states[i] = Joint3DState(None, None, None, None, False)
                            continue

                        u = int(round(float(x)))
                        v = int(round(float(y)))

                        ds = robust_depth_at(
                            # Use depth snapshot captured with this RGB bundle.
                            depth_z16=depth_z16,
                            depth_scale=depth_scale,
                            intr=intr,
                            u=u,
                            v=v,
                            roi=depth_roi,
                            min_valid_ratio=min_valid_ratio,
                            outlier_mad_k=outlier_mad_k,
                        )


                        #  2d 비활성화
                        # ds.valid = False
                        # ds.xyz_m = None

                        if not ds.valid or ds.xyz_m is None:
                            joint_states[i] = Joint3DState(None, None, None, None, False)
                            continue

                        xyz_filt = filters_3d[i](ds.xyz_m, now)
                        joint_xyz[i] = xyz_filt

                        # per-joint speed (optional, only wrists are used)
                        if i in prev_filt:
                            xyz_prev, t_prev = prev_filt[i]
                            dtv = max(now - t_prev, 1e-6)
                            v_xyz = (xyz_filt - xyz_prev) / dtv
                            speed = float(np.linalg.norm(v_xyz))
                        else:
                            v_xyz = None
                            speed = None

                        prev_filt[i] = (xyz_filt, now)
                        joint_states[i] = Joint3DState(ds.xyz_m, xyz_filt, v_xyz, speed, True)

                    def get3(i: int) -> Optional[np.ndarray]:
                        js = joint_states.get(i)
                        if js and js.valid and js.xyz_filt is not None:
                            return js.xyz_filt
                        return None

                    # 상체
                    Ls = get3(KPT["left_shoulder"])
                    Le = get3(KPT["left_elbow"])
                    Lw = get3(KPT["left_wrist"])
                    Rs = get3(KPT["right_shoulder"])
                    Re = get3(KPT["right_elbow"])
                    Rw = get3(KPT["right_wrist"])

                    # 몸통
                    Lh = get3(KPT["left_hip"])
                    Rh = get3(KPT["right_hip"])

                    # 하체
                    Lk = get3(KPT["left_knee"])
                    La = get3(KPT["left_ankle"])
                    Lt = get3(KPT["left_toe"])
                    Lheel = get3(KPT["left_heel"])

                    Rk = get3(KPT["right_knee"])
                    Ra = get3(KPT["right_ankle"])
                    Rt = get3(KPT["right_toe"])
                    Rheel = get3(KPT["right_heel"])

                    shoulder_center = center(Ls, Rs)
                    hip_center = center(Lh, Rh)
                  
                    l_elbow = float(angle_3pts(Ls, Le, Lw))
                
                    r_elbow = float(angle_3pts(Rs, Re, Rw))
        
                    l_shoulder_flex = float(angle_3pts(Lh, Ls, Lw))
                
                    r_shoulder_flex = float(angle_3pts(Rh, Rs, Rw))
                
                    trunk_rot_lat = float(slope_xy(Ls, Rs))
            
                    pelvis_level = float(slope_xy(Lh, Rh))
                
                    trunk_tilt = float(slope_yz(hip_center, shoulder_center))

                    # 무릎 굴곡: Hip - Knee - Ankle
                
                    l_knee_flex = float(angle_3pts(Lh, Lk, La))
            
                    r_knee_flex = float(angle_3pts(Rh, Rk, Ra))

                     # 고관절 굴곡: Shoulder - Hip - Knee
                
                    l_hip_flex = float(angle_3pts(Ls, Lh, Lk))
                
                    r_hip_flex = float(angle_3pts(Rs, Rh, Rk))

                    # 발목 족저굴곡: Knee - Ankle - Toe
                
                    l_ankle_pf = float(angle_3pts(Lk, La, Lt))
                
                    r_ankle_pf = float(angle_3pts(Rk, Ra, Rt))

                # 발목 내번/외번: Knee - Ankle - Heel
                
                    # l_ankle_inv_ev = float(angle_3pts(Lk, La, Lheel))
                
                    # r_ankle_inv_ev = float(angle_3pts(Rk, Ra, Rheel))
                    l_ankle_inv_ev = float(slope_yz(Lt, Lheel))
                
                    r_ankle_inv_ev = float(slope_yz(Rt, Rheel))

                    # 발 뒷꿈치 기울기: Toe - Heel - Vertical Line
                    l_heel_tilt = float(slope_yz(Lt, Lheel))
                    r_heel_tilt = float(slope_yz(Rt, Rheel))


                    lw_state = joint_states.get(KPT["left_wrist"])
                    rw_state = joint_states.get(KPT["right_wrist"])

                    if lw_state and lw_state.valid and lw_state.speed is not None:
                        l_wspd = float(lw_state.speed)
                    if rw_state and rw_state.valid and rw_state.speed is not None:
                        r_wspd = float(rw_state.speed)

                    try:
                        rw_conf = float(kpts_xy[KPT["right_wrist"]][2])
                        lw_conf = float(kpts_xy[KPT["left_wrist"]][2])
                    except Exception:
                        pass

                cur_t = time.time()
                dt = max(cur_t - last_frame_t, 1e-6)
                last_frame_t = cur_t
                fps_inst = 1.0 / dt
                fps_ema = 0.9 * fps_ema + 0.1 * fps_inst

                # write json
                deg_left = {
                    "shoulder_flexion": l_shoulder_flex,
                    "elbow_extension": l_elbow,
                    "ankle_plantarflexion": l_ankle_pf,
                    "knee_flexion": l_knee_flex,
                    "ankle_inversion_eversion": l_ankle_inv_ev,
                    "hip_flexion": l_hip_flex,
                    "heel_tilt": l_heel_tilt,
                }
                deg_right = {
                    "shoulder_flexion": r_shoulder_flex,
                    "elbow_extension": r_elbow,
                    "ankle_plantarflexion": r_ankle_pf,
                    "knee_flexion": r_knee_flex,
                    "ankle_inversion_eversion": r_ankle_inv_ev,
                    "hip_flexion": r_hip_flex,
                    "heel_tilt": r_heel_tilt,
                }
                deg_mid = {
                    "trunk_forward_tilt": trunk_tilt,
                    "trunk_rotation_lateral_flexion": trunk_rot_lat,
                    "pelvis_level": pelvis_level,
                    "trunk_lateral_tilt": trunk_tilt,
                }

                frame_obj = build_frame_from_pose(
                    payload_template=payload_template,
                    frame_idx=frame_idx,
                    video_ms=video_ts_ms,
                    host_ms=host_ts_ms,
                    joint_xyz=joint_xyz,
                    joint_conf=joint_conf,
                    deg_left=deg_left,
                    deg_right=deg_right,
                    deg_mid=deg_mid,
                    strength=imu_v,
                    power=weight_kg,
                )

                frame_obj["camera_sync"] = {
                    "color_ts_ms": float(color_ts_ms) if color_ts_ms is not None else None,
                    "depth_ts_ms": float(depth_ts_ms) if depth_ts_ms is not None else None,
                    "color_frame_number": int(color_frame_no) if color_frame_no is not None else None,
                    "depth_frame_number": int(depth_frame_no) if depth_frame_no is not None else None,
                    "color_depth_delta_ms": (
                        float(depth_ts_ms - color_ts_ms)
                        if (depth_ts_ms is not None and color_ts_ms is not None) else None
                    ),
                    "infer_done_host_ms": float(infer_done_host_ms),
                }

                logger.write_frame(frame_obj)
                frame_idx += 1

                cv2.putText(
                    disp,
                    f"FPS {fps_ema:.1f} conf {conf_th} imu_age {imu_age_out:.0f}ms",
                    (10, disp.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )

                debug_lines = []

                # # arm_raise
                # debug_lines.append("[arm_raise] 팔 들어올리기")
                # debug_lines.append(f"  shoulder_flexion (L/R): {fmt_deg(l_shoulder_flex)}, {fmt_deg(r_shoulder_flex)}")
                # debug_lines.append(f"  elbow_extension (L/R):  {fmt_deg(l_elbow)}, {fmt_deg(r_elbow)}")
                # debug_lines.append(f"  trunk_forward_tilt (M): {fmt_deg(trunk_tilt)}")
                # debug_lines.append(f"  trunk_rot_lat_flex (M): {fmt_deg(trunk_rot_lat)}")
                # debug_lines.append("")  # blank line

                # # single_leg_raise
                # debug_lines.append("[single_leg_raise] 한 쪽 발 올리기")
                # debug_lines.append(f"  ankle_plantarflex (L/R): {fmt_deg(l_ankle_pf)}, {fmt_deg(r_ankle_pf)}")
                # debug_lines.append(f"  knee_flexion (L/R):      {fmt_deg(l_knee_flex)}, {fmt_deg(r_knee_flex)}")
                # debug_lines.append(f"  pelvis_level (M):        {fmt_deg(pelvis_level)}")
                # debug_lines.append(f"  trunk_lateral_tilt (M):  {fmt_deg(trunk_tilt)}")
                # debug_lines.append(f"  ankle_inv_ev (L/R):      {fmt_deg(l_ankle_inv_ev)}, {fmt_deg(r_ankle_inv_ev)}")
                # debug_lines.append(f"  hip_flexion (L/R):       {fmt_deg(l_hip_flex)}, {fmt_deg(r_hip_flex)}")
                # debug_lines.append(f"  heel_tilt (L/R):         {fmt_deg(l_heel_tilt)}, {fmt_deg(r_heel_tilt)}")

                debug_lines.append(f"  power:         {weight_kg}")

                put_lines(disp, x=10, y=25, lines=debug_lines, scale=0.55, thickness=2, line_gap=18)

                cv2.imshow(win_name, disp)
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or key == ord("q"):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            trt_engine.close()
        except Exception:
            pass
        try:
            imu.stop()
        except Exception:
            pass
        try:
            if load_cell is not None:
                load_cell.stop()
        except Exception:
            pass
        try:
            logger.close()
        except Exception:
            pass


if __name__ == "__main__":
    os.environ["DISPLAY"] = ":0"

    config_path = os.getenv("CONFIG_PATH", "configs/pose_sensor_fusion/run.yaml")
    cfg = load_yaml_config(config_path)
    main(cfg)
