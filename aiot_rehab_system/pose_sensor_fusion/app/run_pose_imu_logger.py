#!/usr/bin/env python3

import os
import time
import math
from typing import Dict, Optional, Tuple, List, Any

import cv2
import numpy as np

from pose_sensor_fusion.imu.udp_buffer import ImuUdpBuffer
from pose_sensor_fusion.log.csv_logger import CsvLogger

from pose_sensor_fusion.vendor.realsense_ai_api import RealSenseAIApi, FrameBundle
import pose_sensor_fusion.vendor.yolo11m_vDepth as pose

from pose_sensor_fusion.utils.config_loader import load_yaml_config


def _nan3():
    return [float("nan"), float("nan"), float("nan")]


def _flat3(xyz: Optional[np.ndarray]):
    if xyz is None:
        return _nan3()
    return [float(xyz[0]), float(xyz[1]), float(xyz[2])]


def _finite_xyz(xyz: Optional[np.ndarray]) -> bool:
    if xyz is None:
        return False
    return bool(np.isfinite(xyz).all())


def build_header_full17() -> List[str]:
    header = [
        "frame_idx",
        "video_ts_ms",
        "host_ts_ms",
        "fps_ema",
        "imu_v_cmps",
        "imu_seq",
        "imu_ts_ms",
        "imu_age_ms",
        "imu_used_interp",
        "r_elbow_deg",
        "l_elbow_deg",
        "r_wrist_speed_mps",
        "l_wrist_speed_mps",
    ]

    # 17 joints: 3D position in camera coords (meters), plus 2D conf score
    # naming: j{idx}_x_m, j{idx}_y_m, j{idx}_z_m, j{idx}_conf
    for j in range(17):
        header += [f"j{j}_x_m", f"j{j}_y_m", f"j{j}_z_m", f"j{j}_conf"]

    # optional quick access for wrists conf, handy
    header += ["rw_conf", "lw_conf"]
    return header


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


    imu = ImuUdpBuffer(
        listen_ip=imu_cfg["udp_ip"], 
        listen_port=imu_cfg["udp_port"], 
        max_age_sec=imu_cfg["buffer_sec"]
    )

    imu.start()

    logger = CsvLogger(cfg["logging"]["output_dir"], prefix="pose_imu_full17")
    header = build_header_full17()
    logger.write_header(header)

    print(f"[LOG] CSV -> {logger.path}")
    print(f"[IMU] udp :{imu_cfg['udp_port']} match={IMU_MATCH} buffer={imu_cfg['buffer_sec']:.1f}s")

    trt_engine = pose.TrtEngine(engine_path)
    filters_3d: Dict[int, pose.OneEuroFilter3D] = {
        i: pose.OneEuroFilter3D(filt_min_cutoff, filt_beta, filt_d_cutoff) for i in range(17)
    }
    prev_filt: Dict[int, Tuple[np.ndarray, float]] = {}

    st = pose.TrackState()
    fps_ema = 0.0
    last_frame_t = time.time()
    frame_idx = 0

    win_name = "Pose+Depth+IMU Logger (full17)"

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
                    imu_v = float(imu_s.v_cmps)
                    imu_seq = int(imu_s.seq)
                    imu_ts = int(imu_s.imu_ts_ms)
                    imu_age_out = float(imu_age_ms)

                inp, scale, dx, dy = pose.preprocess_bgr_letterbox(frame, 640)
                out_trt = trt_engine.infer(inp)

                boxes, scores, kpts = pose.decode_pose(out_trt, conf_th=conf_th, iou_th=iou_th)
                pick = pose.pick_person(boxes, scores, kpts, st, stick_iou=stick_iou)

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

                # Outputs to store
                joint_xyz_17: List[Optional[np.ndarray]] = [None] * 17
                joint_conf_17: List[float] = [float("nan")] * 17

                r_elbow = float("nan")
                l_elbow = float("nan")
                r_wspd = float("nan")
                l_wspd = float("nan")
                rw_conf = float("nan")
                lw_conf = float("nan")

                if kpts_640 is not None:
                    kpts_xy = pose.unletterbox_points(kpts_640.reshape(-1, 3), scale, dx, dy)
                    pose.draw_pose_2d(disp, kpts_xy, kp_th=kp_th)

                    joint_states: Dict[int, pose.Joint3DState] = {}

                    for i in range(17):
                        x, y, s = kpts_xy[i]
                        joint_conf_17[i] = float(s)

                        if float(s) < kp_th:
                            joint_states[i] = pose.Joint3DState(None, None, None, None, False)
                            continue

                        u = int(round(float(x)))
                        v = int(round(float(y)))

                        ds = pose.robust_depth_at(
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
                            joint_states[i] = pose.Joint3DState(None, None, None, None, False)
                            continue

                        xyz_filt = filters_3d[i](ds.xyz_m, now)
                        joint_xyz_17[i] = xyz_filt

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
                        joint_states[i] = pose.Joint3DState(ds.xyz_m, xyz_filt, v_xyz, speed, True)

                    def get3(i: int) -> Optional[np.ndarray]:
                        js = joint_states.get(i)
                        if js and js.valid and js.xyz_filt is not None:
                            return js.xyz_filt
                        return None

                    Ls = get3(pose.COCO["L_SHOULDER"])
                    Le = get3(pose.COCO["L_ELBOW"])
                    Lw = get3(pose.COCO["L_WRIST"])
                    Rs = get3(pose.COCO["R_SHOULDER"])
                    Re = get3(pose.COCO["R_ELBOW"])
                    Rw = get3(pose.COCO["R_WRIST"])

                    if _finite_xyz(Ls) and _finite_xyz(Le) and _finite_xyz(Lw):
                        l_elbow = float(pose.angle_3pts(Ls, Le, Lw))
                    if _finite_xyz(Rs) and _finite_xyz(Re) and _finite_xyz(Rw):
                        r_elbow = float(pose.angle_3pts(Rs, Re, Rw))

                    lw_state = joint_states.get(pose.COCO["L_WRIST"])
                    rw_state = joint_states.get(pose.COCO["R_WRIST"])
                    if lw_state and lw_state.valid and lw_state.speed is not None:
                        l_wspd = float(lw_state.speed)
                    if rw_state and rw_state.valid and rw_state.speed is not None:
                        r_wspd = float(rw_state.speed)

                    try:
                        rw_conf = float(kpts_xy[pose.COCO["R_WRIST"]][2])
                        lw_conf = float(kpts_xy[pose.COCO["L_WRIST"]][2])
                    except Exception:
                        pass

                cur_t = time.time()
                dt = max(cur_t - last_frame_t, 1e-6)
                last_frame_t = cur_t
                fps_inst = 1.0 / dt
                fps_ema = 0.9 * fps_ema + 0.1 * fps_inst

                # write CSV row
                row = [
                    frame_idx,
                    video_ts_ms,
                    host_ts_ms,
                    float(fps_ema),
                    imu_v,
                    imu_seq,
                    imu_ts,
                    float(imu_age_out),
                    int(bool(used_interp)),
                    r_elbow,
                    l_elbow,
                    r_wspd,
                    l_wspd,
                ]

                for j in range(17):
                    row += _flat3(joint_xyz_17[j])
                    row += [float(joint_conf_17[j])]

                row += [rw_conf, lw_conf]

                logger.write_row(row)
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
            logger.close()
        except Exception:
            pass


if __name__ == "__main__":

    config_path = os.getenv("CONFIG_PATH", "configs/pose_sensor_fusion/default.yaml")
    cfg = load_yaml_config(config_path)
    main(cfg)