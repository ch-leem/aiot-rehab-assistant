#!/usr/bin/env python3
import os
import time
import math
import threading
import asyncio
import signal
from typing import Dict, Optional, Tuple, List, Any, Mapping

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
    KPT,
    Joint3DState,
)

from pose_sensor_fusion.utils.config_loader import load_yaml_config
from pose_sensor_fusion.utils.create_payload import load_data_payload, build_frame_from_pose

from pose_sensor_fusion.utils.ingest_sender import IngestSender
from pose_sensor_fusion.utils.webrtc_streamer import LatestFrameBuffer, WebRTCStreamer, WebRTCConfig

from pose_sensor_fusion.utils.calculate import fmt_deg, put_lines, _finite_xyz, angle_3pts, slope_xy, slope_yz, center

GLOBAL_STOP_FLAG = None
GLOBAL_STREAMER = None

def get3(joint_states: Mapping[int, "Joint3DState"], i: int) -> Optional[np.ndarray]:
    js = joint_states.get(i)
    if js and js.valid and js.xyz_filt is not None:
        return js.xyz_filt
    return None

def _handle_exit(sig, frame):
    if GLOBAL_STOP_FLAG is not None:
        GLOBAL_STOP_FLAG.set()
    try:
        if GLOBAL_STREAMER is not None:
            GLOBAL_STREAMER.stop()
    except Exception:
        pass

signal.signal(signal.SIGTERM, _handle_exit)
signal.signal(signal.SIGINT, _handle_exit)

def main_loop(cfg: Dict[str, Any], buf: LatestFrameBuffer, stop_flag: threading.Event) -> None:
    
    # 설정값 로드
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
    LC_MATCH = lc_cfg.get("match", "nearest")
    LC_MAX_ABS_AGE_MS = float(lc_cfg.get("max_abs_age_ms", 500.0))

    num_joints = cfg["inference"]["num_joints"]

    is_ingest = bool(cfg["ingest"]["enable"])
    is_webrtc_in = bool(cfg["webrtc"].get("enable", True))

    is_local_vis = bool(cfg["local_vis"]["enable"])

    # 센서 모듈 시작
    imu = ImuUdpBuffer(
        listen_ip=imu_cfg["udp_ip"],
        listen_port=imu_cfg["udp_port"],
        max_age_sec=imu_cfg["buffer_sec"],
    )
    imu.start()

    load_cell = WeightUdpBuffer(
        listen_ip=lc_cfg.get("udp_ip", "0.0.0.0"),
        listen_port=int(lc_cfg.get("udp_port", 9998)),
        max_age_sec=float(lc_cfg.get("buffer_sec", 8.0)),
    )
    load_cell.start()

    # 데이터 템플릿 로드
    payload_template = load_data_payload(cfg["logging"]["payload_path"])

    # Redis 서버 Ingest 통신 시작

    sender = None

    if is_ingest:
        ingest_url = cfg["ingest"]["url"]
        sender = IngestSender(
            url=ingest_url,
            max_queue=int(cfg["ingest"]["max_queue"]),
            timeout_sec=float(cfg["ingest"]["timeout_sec"]),
            drop_policy=cfg["ingest"]["drop_policy"],
        )
        sender.start()

    # print(f"[INGEST] POST {ingest_url} queue={sender.maxsize} timeout={sender.timeout_sec}s policy={sender.drop_policy}")

    # TensorRT 엔진 로드
    trt_engine = TrtEngine(engine_path)

    # 3D 관절 필터 초기화
    filters_3d = {i: OneEuroFilter3D(filt_min_cutoff, filt_beta, filt_d_cutoff) for i in range(num_joints)}
    prev_filt: Dict[int, Tuple[np.ndarray, float]] = {}

    # 메인 루프 초기화
    st = TrackState()
    fps_ema = 0.0
    last_frame_t = time.time()
    frame_idx = 0

    win_name = "pose21_strength_power"

    try:
        # RealSense 카메라 시작
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

            # 카메라 내부 파라미터 및 깊이 스케일 가져오기
            intr = cam.rgb_intrinsics()
            depth_scale = cam.depth_scale()
            if depth_scale is None:
                raise RuntimeError("Depth scale is None")

            if is_local_vis:
                cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(win_name, 1280, 960)

            while not stop_flag.is_set():
                bundle: FrameBundle = cam.get_frames(want_depth_frame=True, postprocess_depth=False)
                frame = bundle.rgb
                depth_z16 = bundle.depth
                if frame is None or depth_z16 is None:
                    continue

                video_ts_ms = float(bundle.timestamp_ms)
                host_ts_ms = time.time() * 1000.0

                # IMU 및 하체 힘 데이터 매칭

                if IMU_MATCH == "interp":
                    imu_s, imu_age_ms, used_interp = imu.match_interp(host_ts_ms)
                else:
                    imu_s, imu_age_ms = imu.match_nearest(host_ts_ms)
                    used_interp = False

                if imu_s is None or abs(imu_age_ms) > IMU_MAX_ABS_AGE_MS:
                    imu_v = float("nan")
                    imu_age_out = float("inf")
                else:
                    imu_v = float(imu_s.strength_cmps)
                    imu_age_out = float(imu_age_ms)

                if LC_MATCH == "interp":
                    w_s, w_age_ms, weight_used_interp = load_cell.match_interp(host_ts_ms)
                else:
                    w_s, w_age_ms = load_cell.match_nearest(host_ts_ms)
                    weight_used_interp = False

                if w_s is None or abs(w_age_ms) > LC_MAX_ABS_AGE_MS:
                    weight_kg = float("nan")
                else:
                    weight_kg = float(w_s.weight_kg)

                # 포즈 추정
                inp, scale, dx, dy = preprocess_bgr_letterbox(frame, 640)
                out_trt = trt_engine.infer(inp)

                boxes, scores, kpts = decode_pose(out_trt, conf_th=conf_th, iou_th=iou_th)
                pick = pick_person(boxes, scores, kpts, st, stick_iou=stick_iou)

                now = time.time()

                # 추적 상태 업데이트
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

                # 3D 관절 위치 계산 및 필터링
                disp = frame.copy()

                # 초기화
                joint_xyz: List[Optional[np.ndarray]] = [None] * num_joints
                joint_conf: List[float] = [None] * num_joints

                l_shoulder_flex = float("nan")
                r_shoulder_flex = float("nan")
                l_elbow = float("nan")
                r_elbow = float("nan")
                trunk_tilt = float("nan")
                trunk_rot_lat = float("nan")
                pelvis_level = float("nan")

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

                    # 2D 포즈 그리기
                    kpts_xy = unletterbox_points(kpts_640.reshape(-1, 3), scale, dx, dy)
                    draw_pose_2d(disp, kpts_xy, kp_th=kp_th)

                    joint_states: Dict[int, Joint3DState] = {}

                    # 각 관절에 대해 깊이값 추출 및 3D 좌표 계산
                    for i in range(num_joints):
                        x, y, s = kpts_xy[i]
                        joint_conf[i] = float(s)

                        if float(s) < kp_th:
                            joint_states[i] = Joint3DState(None, None, None, None, False)
                            continue

                        u = int(round(float(x)))
                        v = int(round(float(y)))

                        ds = robust_depth_at(
                            depth_z16=depth_z16,
                            depth_scale=depth_scale,
                            intr=intr,
                            u=u,
                            v=v,
                            roi=depth_roi,
                            min_valid_ratio=min_valid_ratio,
                            outlier_mad_k=outlier_mad_k,
                        )

                        if not ds.valid or ds.xyz_m is None:
                            joint_states[i] = Joint3DState(None, None, None, None, False)
                            continue

                        xyz_filt = filters_3d[i](ds.xyz_m, now)
                        joint_xyz[i] = xyz_filt
                        prev_filt[i] = (xyz_filt, now)
                        joint_states[i] = Joint3DState(ds.xyz_m, xyz_filt, None, None, True)

                    # 각종 각도 및 기울기 계산

                    Ls = get3(joint_states, KPT["left_shoulder"])
                    Le = get3(joint_states, KPT["left_elbow"])
                    Lw = get3(joint_states, KPT["left_wrist"])
                    Rs = get3(joint_states, KPT["right_shoulder"])
                    Re = get3(joint_states, KPT["right_elbow"])
                    Rw = get3(joint_states, KPT["right_wrist"])

                    Lh = get3(joint_states, KPT["left_hip"])
                    Rh = get3(joint_states, KPT["right_hip"])
                    Lk = get3(joint_states, KPT["left_knee"])
                    La = get3(joint_states, KPT["left_ankle"])
                    Lt = get3(joint_states, KPT["left_toe"])

                    Rk = get3(joint_states, KPT["right_knee"])
                    Ra = get3(joint_states, KPT["right_ankle"])
                    Rt = get3(joint_states, KPT["right_toe"])

                    shoulder_center = center(Ls, Rs)
                    hip_center = center(Lh, Rh)

                    l_elbow = float(angle_3pts(Ls, Le, Lw))
                    r_elbow = float(angle_3pts(Rs, Re, Rw))

                    l_shoulder_flex = float(angle_3pts(Lh, Ls, Lw))
                    r_shoulder_flex = float(angle_3pts(Rh, Rs, Rw))

                    trunk_rot_lat = float(slope_xy(Ls, Rs))
                    pelvis_level = float(slope_xy(Lh, Rh))
                    trunk_tilt = float(slope_yz(hip_center, shoulder_center))

                    l_knee_flex = float(angle_3pts(Lh, Lk, La))
                    r_knee_flex = float(angle_3pts(Rh, Rk, Ra))

                    l_hip_flex = float(angle_3pts(Ls, Lh, Lk))
                    r_hip_flex = float(angle_3pts(Rs, Rh, Rk))

                    l_ankle_pf = float(angle_3pts(Lk, La, Lt))
                    r_ankle_pf = float(angle_3pts(Rk, Ra, Rt))

                # 프레임당 처리 시간 및 FPS 계산

                cur_t = time.time()
                dt = max(cur_t - last_frame_t, 1e-6)
                last_frame_t = cur_t
                fps_inst = 1.0 / dt
                fps_ema = 0.9 * fps_ema + 0.1 * fps_inst

                # 데이터 페이로드 작성 및 전송
                deg_left = {
                    "shoulder_flexion": l_shoulder_flex,
                    "elbow_extension": l_elbow,
                    "ankle_plantarflexion": l_ankle_pf,
                    "knee_flexion": l_knee_flex,
                    "hip_flexion": l_hip_flex,
                    "heel_tilt": l_heel_tilt,
                    "ankle_inversion_eversion": l_ankle_inv_ev,
                }
                deg_right = {
                    "shoulder_flexion": r_shoulder_flex,
                    "elbow_extension": r_elbow,
                    "ankle_plantarflexion": r_ankle_pf,
                    "knee_flexion": r_knee_flex,
                    "hip_flexion": r_hip_flex,
                    "heel_tilt": r_heel_tilt,
                    "ankle_inversion_eversion": r_ankle_inv_ev,
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

                if is_ingest:
                    sender.push({"frames": [frame_obj]})

                # cv2.putText(
                #     disp,
                #     f"FPS {fps_ema:.1f}",
                #     (10, disp.shape[0] - 15),
                #     cv2.FONT_HERSHEY_SIMPLEX,
                #     0.7,
                #     (0, 255, 0),
                #     2,
                # )

                # WebRTC로 보낼 프레임 push
                if is_webrtc_in:
                    buf.push(disp, {"frame_idx": frame_idx, "host_ts_ms": host_ts_ms})

                # debug_lines = []

                # # arm_raise
                # debug_lines.append("[arm_raise] 팔 들어올리기")
                # debug_lines.append(f"  shoulder_flexion (L/R): {fmt_deg(l_shoulder_flex)}, {fmt_deg(r_shoulder_flex)}")
                # debug_lines.append(f"  elbow_extension (L/R):  {fmt_deg(l_elbow)}, {fmt_deg(r_elbow)}")
                # debug_lines.append(f"  trunk_forward_tilt (M): {fmt_deg(trunk_tilt)}")
                # debug_lines.append(f"  trunk_rot_lat_flex (M): {fmt_deg(trunk_rot_lat)}")
                # debug_lines.append("")  # blank line

                # # single_leg_raise
                # # debug_lines.append("[single_leg_raise] 한 쪽 발 올리기")
                # # debug_lines.append(f"  ankle_plantarflex (L/R): {fmt_deg(l_ankle_pf)}, {fmt_deg(r_ankle_pf)}")
                # # debug_lines.append(f"  knee_flexion (L/R):      {fmt_deg(l_knee_flex)}, {fmt_deg(r_knee_flex)}")
                # # debug_lines.append(f"  pelvis_level (M):        {fmt_deg(pelvis_level)}")
                # # debug_lines.append(f"  trunk_lateral_tilt (M):  {fmt_deg(trunk_tilt)}")
                # # debug_lines.append(f"  ankle_inv_ev (L/R):      {fmt_deg(l_ankle_inv_ev)}, {fmt_deg(r_ankle_inv_ev)}")
                # # debug_lines.append(f"  hip_flexion (L/R):       {fmt_deg(l_hip_flex)}, {fmt_deg(r_hip_flex)}")
                # # debug_lines.append(f"  heel_tilt (L/R):         {fmt_deg(l_heel_tilt)}, {fmt_deg(r_heel_tilt)}")

                # debug_lines.append(f"  strength      :         {imu_v}")
                # debug_lines.append(f"  power      :            {weight_kg}")
                # put_lines(disp, x=10, y=25, lines=debug_lines, scale=0.55, thickness=2, line_gap=18)

                if is_local_vis:
                    cv2.imshow(win_name, disp)
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27 or key == ord("q"):
                        break

                frame_idx += 1

    except KeyboardInterrupt:
        pass
    finally:
        stop_flag.set()
        try:
            if sender is not None:
                sender.stop()
        except Exception:
            pass
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
            load_cell.stop()
        except Exception:
            pass


async def main_async():
    os.environ["DISPLAY"] = ":0"

    config_path = os.getenv("CONFIG_PATH", "configs/pose_sensor_fusion/run.yaml")
    cfg = load_yaml_config(config_path)

    is_webrtc = bool(cfg.get("webrtc", {}).get("enable", True))

    buf = LatestFrameBuffer()
    stop_flag = threading.Event()

    global GLOBAL_STOP_FLAG
    GLOBAL_STOP_FLAG = stop_flag

    if not is_webrtc:
        print("[WebRTC] disabled, run main_loop only (no ws connection).")
        main_loop(cfg, buf, stop_flag)  # 여기서 블로킹으로 계속 돈다
        return

    # WebRTC 켜진 경우만, 기존 구조 유지
    t = threading.Thread(target=main_loop, args=(cfg, buf, stop_flag), daemon=True)
    t.start()

    ws_url = cfg["webrtc"]["url"]
    fps = int(cfg["stream"]["fps"])

    webrtc_cfg = WebRTCConfig(
        ws_url=ws_url,
        fps=fps,
        enable_telemetry=True,
        telemetry_hz=10.0,
    )
    streamer = WebRTCStreamer(buf, webrtc_cfg)

    global GLOBAL_STREAMER
    GLOBAL_STREAMER = streamer

    try:
        await streamer.run()
    finally:
        stop_flag.set()
        t.join(timeout=2.0)

if __name__ == "__main__":
    asyncio.run(main_async())
