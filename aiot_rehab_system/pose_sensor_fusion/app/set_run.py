#!/usr/bin/env python3
import os
import time
from typing import Dict, Any, Optional

import cv2
import numpy as np
import serial  
import asyncio


from pose_sensor_fusion.vision_utills.realsense_ai_api import RealSenseAIApi, FrameBundle
from pose_sensor_fusion.vision_utills.inference.trt_engine import TrtEngine
from pose_sensor_fusion.vision_utills.preprocess.img_preprocessing import (
    preprocess_bgr_letterbox,
    unletterbox_points,
)
from pose_sensor_fusion.vision_utills.pose2d.pose_2d_postprocessing import (
    decode_pose,
    pick_person,
    TrackState,
)
from pose_sensor_fusion.vision_utills.visualize.visualize_pose import draw_pose_2d
from pose_sensor_fusion.utils.config_loader import load_yaml_config

from aiot_rehab_system.pose_sensor_fusion.app.rehab_start import main_async as run_async

def all_joints_visible_2d(kpts_640: Optional[np.ndarray], th: float) -> bool:
    if kpts_640 is None:
        return False
    conf = kpts_640.reshape(-1, 3)[:, 2]
    return bool(np.all(conf >= th))


def check_pose(cfg: Dict[str, Any]) -> None:
    # -----------------------------
    # Config
    # -----------------------------
    engine_path = cfg["engine"]["path"]

    conf_th = float(cfg["inference"]["conf_th"])
    iou_th = float(cfg["inference"]["iou_th"])
    hold_sec = float(cfg["tracking"]["hold_sec"])
    stick_iou = float(cfg["tracking"]["stick_iou"])

    rgb_w = int(cfg["stream"]["rgb"]["width"])
    rgb_h = int(cfg["stream"]["rgb"]["height"])
    fps = int(cfg["stream"]["fps"])

    # draw용(시각화) threshold
    draw_kp_th = float(cfg["inference"]["kp_th"])

    # OK 판정용 threshold
    vis_th = 0.9

    # OK가 몇 프레임 연속이면 '정렬 완료'로 볼지
    ok_need_frames = int(cfg.get("align", {}).get("ok_need_frames", 25))

    # 아두이노 시리얼 포트 (환경에 맞게 바꾸기)
    serial_port = cfg.get("align", {}).get("serial_port", "/dev/ttyACM0")
    serial_baud = int(cfg.get("align", {}).get("serial_baud", 115200))

    # 뒤로 이동 스텝 (abs pos 기준으로 누적)
    step_delta = int(cfg.get("align", {}).get("step_delta", 300))
    move_time_ms = int(cfg.get("align", {}).get("move_time_ms", 1000))

    # MOVE 명령 최소 간격 (초)
    cmd_cooldown_sec = float(cfg.get("align", {}).get("cmd_cooldown_sec", 0.8))

    # 절대 이동 범위 제한 (펌웨어 LIMIT 0..17500과 맞추는게 좋음)
    step_min = int(cfg.get("align", {}).get("step_min", 0))
    step_max = int(cfg.get("align", {}).get("step_max", 17500))

    # "뒤로" 방향이 +인지 -인지 (처음엔 +로 두고, 반대면 -로 바꾸면 됨)
    back_dir = int(cfg.get("align", {}).get("back_dir", +1))

    # 로그 출력 주기
    print_interval_sec = float(cfg.get("align", {}).get("print_interval_sec", 0.25))

    # -----------------------------
    # Init
    # -----------------------------
    trt_engine = TrtEngine(engine_path)
    st = TrackState()

    # 시리얼 연결
    ser = serial.Serial(serial_port, serial_baud, timeout=0.05)
    time.sleep(2.0)  # 아두이노 리셋 대기

    # 현재 abs pos를 모르면 0부터 시작 (필요하면 POS?로 동기화 가능)
    step_pos = step_min

    ok_cnt = 0
    last_cmd_t = 0.0
    last_print_t = 0.0

    win_name = "pose_align_move_back"

    try:
        with RealSenseAIApi(
            rgb_size=(rgb_w, rgb_h),
            depth_size=(rgb_w, rgb_h),
            fps=fps,
            enable_depth=False,
            align_depth_to="color",
            rgb_format="bgr",
            timeout_ms=2000,
        ) as cam:

            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_name, 1280, 960)

            while True:
                bundle: FrameBundle = cam.get_frames(want_depth_frame=False, postprocess_depth=False)
                frame = bundle.rgb
                if frame is None:
                    continue

                # OpenCV putText 호환 보장
                frame = np.ascontiguousarray(frame.copy())

                # -----------------------------
                # Pose inference
                # -----------------------------
                inp, scale, dx, dy = preprocess_bgr_letterbox(frame, 640)
                out_trt = trt_engine.infer(inp)

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

                # -----------------------------
                # 2D OK/NO 판정 (vis_th 기준)
                # -----------------------------
                ok_now = all_joints_visible_2d(kpts_640, th=vis_th)
                if ok_now:
                    ok_cnt += 1
                else:
                    ok_cnt = 0

                aligned = (ok_cnt >= ok_need_frames)

                # -----------------------------
                # NO가 지속되면 조금씩 뒤로 MOVE
                # -----------------------------
                t_now = time.time()
                if (not aligned) and ((t_now - last_cmd_t) >= cmd_cooldown_sec):
                    # 뒤로 이동 목표 abs pos 갱신
                    step_pos = step_pos + back_dir * step_delta
                    if step_pos < step_min:
                        step_pos = step_min
                    if step_pos > step_max:
                        step_pos = step_max
                    
                    print(f"Sending MOVE {step_pos} {move_time_ms}")
                    ser.write(f"MOVE {step_pos} {move_time_ms}\n".encode("utf-8"))
                    last_cmd_t = t_now

                # aligned면 정지 명령 1회 보내기(원하면)
                if aligned and ((t_now - last_cmd_t) >= cmd_cooldown_sec):
                    ser.write(b"STOP\n")
                    last_cmd_t = t_now
                    return

                # -----------------------------
                # Debug print
                # -----------------------------
                if (t_now - last_print_t) >= print_interval_sec:
                    if kpts_640 is None:
                        print(f"NO (no pose) ok_cnt={ok_cnt}/{ok_need_frames} step_pos={step_pos}")
                    else:
                        conf = kpts_640.reshape(-1, 3)[:, 2]
                        print(
                            f"{'OK' if ok_now else 'NO'} "
                            f"min={conf.min():.2f} mean={conf.mean():.2f} "
                            f"ok_cnt={ok_cnt}/{ok_need_frames} step_pos={step_pos}"
                        )
                    last_print_t = t_now

                # -----------------------------
                # Visualization (draw_kp_th=0.25 기준)
                # -----------------------------
                disp = frame
                if kpts_640 is not None:
                    kpts_xy = unletterbox_points(kpts_640.reshape(-1, 3), scale, dx, dy)
                    draw_pose_2d(disp, kpts_xy, kp_th=draw_kp_th)

                cv2.putText(
                    disp,
                    f"{'ALIGNED' if aligned else 'ALIGNING'}  vis_th={vis_th:.2f} draw_th={draw_kp_th:.2f}  ok={ok_cnt}/{ok_need_frames}  pos={step_pos}",
                    (10, disp.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0) if aligned else (0, 0, 255),
                    2,
                )

                cv2.imshow(win_name, disp)
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or key == ord("q"):
                    break

    finally:
        try:
            ser.write(b"STOP\n")
        except Exception:
            pass
        try:
            ser.close()
        except Exception:
            pass
        try:
            trt_engine.close()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


def main():
    os.environ["DISPLAY"] = ":0"
    config_path = os.getenv(
        "CONFIG_PATH",
        "/home/a203/workspace/S14P11A203/aiot_rehab_system/configs/pose_sensor_fusion/run.yaml",
    )
    cfg = load_yaml_config(config_path)
    check_pose(cfg)

    asyncio.run(run_async())

if __name__ == "__main__":
    main()
