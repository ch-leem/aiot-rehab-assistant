#!/usr/bin/env python3
import os
import time
import math
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from pose_imu_logger.config import IMU_UDP_IP, IMU_UDP_PORT, IMU_MATCH, IMU_BUFFER_SEC, IMU_MAX_ABS_AGE_MS, LOG_DIR
from pose_imu_logger.imu.udp_buffer import ImuUdpBuffer
from pose_imu_logger.log.csv_logger import CsvLogger

# vendor stack (your uploaded code)
from pose_imu_logger.vendor.realsense_ai_api import RealSenseAIApi, FrameBundle
import pose_imu_logger.vendor.yolo11m_vDepth as pose


def _nan3():
    return [float("nan"), float("nan"), float("nan")]


def _flat3(xyz: Optional[np.ndarray]):
    if xyz is None:
        return _nan3()
    return [float(xyz[0]), float(xyz[1]), float(xyz[2])]


def main():
    # --- Keep env compatibility with original yolo11m_vDepth.py ---
    engine_path = os.getenv("ENGINE_PATH", "/home/a203/yolo11m-pose_fp16.engine")

    conf_th = float(os.getenv("CONF_TH", "0.25"))
    iou_th = float(os.getenv("IOU_TH", "0.45"))
    kp_th = float(os.getenv("KP_TH", "0.25"))

    hold_sec = float(os.getenv("HOLD_SEC", "0.5"))
    stick_iou = float(os.getenv("STICK_IOU", "0.2"))

    depth_roi = int(os.getenv("DEPTH_ROI", "5"))
    min_valid_ratio = float(os.getenv("DEPTH_MIN_VALID_RATIO", "0.25"))
    outlier_mad_k = float(os.getenv("DEPTH_OUTLIER_MAD_K", "3.5"))

    filt_min_cutoff = float(os.getenv("FILT_MIN_CUTOFF", "1.5"))
    filt_beta = float(os.getenv("FILT_BETA", "0.02"))
    filt_d_cutoff = float(os.getenv("FILT_D_CUTOFF", "1.0"))

    rgb_w = int(os.getenv("RGB_W", "640"))
    rgb_h = int(os.getenv("RGB_H", "480"))
    fps = int(os.getenv("FPS", "30"))

    # --- IMU receiver + CSV logger ---
    imu = ImuUdpBuffer(listen_ip=IMU_UDP_IP, listen_port=IMU_UDP_PORT, max_age_sec=IMU_BUFFER_SEC)
    imu.start()

    logger = CsvLogger(LOG_DIR, prefix="pose_imu")
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
        "rs_x","rs_y","rs_z",
        "re_x","re_y","re_z",
        "rw_x","rw_y","rw_z",
        "ls_x","ls_y","ls_z",
        "le_x","le_y","le_z",
        "lw_x","lw_y","lw_z",
        "rw_conf","lw_conf",
    ]
    logger.write_header(header)

    print(f"[LOG] CSV -> {logger.path}")
    print(f"[IMU] udp :{IMU_UDP_PORT} match={IMU_MATCH} buffer={IMU_BUFFER_SEC:.1f}s")

    trt_engine = pose.TrtEngine(engine_path)
    filters_3d: Dict[int, pose.OneEuroFilter3D] = {i: pose.OneEuroFilter3D(filt_min_cutoff, filt_beta, filt_d_cutoff) for i in range(17)}
    prev_filt: Dict[int, Tuple[np.ndarray, float]] = {}

    st = pose.TrackState()
    fps_ema = 0.0
    last_frame_t = time.time()
    frame_idx = 0

    win_name = "Pose+Depth+IMU CSV Logger"

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

                # IMU match on host clock (stable for UDP)
                if IMU_MATCH == "interp":
                    imu_s, imu_age_ms, used_interp = imu.match_interp(host_ts_ms)
                else:
                    imu_s, imu_age_ms = imu.match_nearest(host_ts_ms)
                    used_interp = False

                # apply max age gate
                if imu_s is None or abs(imu_age_ms) > IMU_MAX_ABS_AGE_MS:
                    imu_v = float("nan"); imu_seq = -1; imu_ts = -1
                else:
                    imu_v = float(imu_s.v_cmps)
                    imu_seq = int(imu_s.seq)
                    imu_ts = int(imu_s.imu_ts_ms)

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
                joint_states: Dict[int, pose.Joint3DState] = {}

                Rs = Re = Rw = Ls = Le = Lw = None
                rw_conf = lw_conf = float("nan")
                r_elbow = l_elbow = float("nan")
                r_wspd = l_wspd = float("nan")

                if kpts_640 is not None:
                    kpts_xy = pose.unletterbox_points(kpts_640.reshape(-1, 3), scale, dx, dy)
                    pose.draw_pose_2d(disp, kpts_xy, kp_th=kp_th)

                    # build 3D + speed
                    for i in range(17):
                        x, y, s = kpts_xy[i]
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

                        xyz_raw = ds.xyz_m
                        xyz_filt = filters_3d[i](xyz_raw, now)

                        if i in prev_filt:
                            xyz_prev, t_prev = prev_filt[i]
                            dt = max(now - t_prev, 1e-6)
                            v_xyz = (xyz_filt - xyz_prev) / dt
                            speed = float(np.linalg.norm(v_xyz))
                        else:
                            v_xyz = None
                            speed = None

                        prev_filt[i] = (xyz_filt, now)
                        joint_states[i] = pose.Joint3DState(xyz_raw, xyz_filt, v_xyz, speed, True)

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

                    if Ls is not None and Le is not None and Lw is not None:
                        l_elbow = float(pose.angle_3pts(Ls, Le, Lw))
                    if Rs is not None and Re is not None and Rw is not None:
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

                # FPS estimate
                cur_t = time.time()
                dt = max(cur_t - last_frame_t, 1e-6)
                last_frame_t = cur_t
                fps_inst = 1.0 / dt
                fps_ema = 0.9 * fps_ema + 0.1 * fps_inst

                # CSV row per frame
                row = [
                    frame_idx,
                    video_ts_ms,
                    host_ts_ms,
                    float(fps_ema),
                    imu_v,
                    imu_seq,
                    imu_ts,
                    float(imu_age_ms if imu_s is not None else float("inf")),
                    int(used_interp),
                    r_elbow,
                    l_elbow,
                    r_wspd,
                    l_wspd,
                    *_flat3(Rs),
                    *_flat3(Re),
                    *_flat3(Rw),
                    *_flat3(Ls),
                    *_flat3(Le),
                    *_flat3(Lw),
                    rw_conf,
                    lw_conf,
                ]
                logger.write_row(row)
                frame_idx += 1

                # Overlay + show
                cv2.putText(disp, f"FPS {fps_ema:.1f}  conf {conf_th}", (10, disp.shape[0] - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

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
    main()
