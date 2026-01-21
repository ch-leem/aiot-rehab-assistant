#!/usr/bin/env python3
import os
import time
from typing import Dict, Any, Optional

import cv2
import numpy as np

from pose_sensor_fusion.vision_utills.realsense_ai_api import RealSenseAIApi, FrameBundle
from pose_sensor_fusion.vision_utills.inference.trt_engine import TrtEngine
from pose_sensor_fusion.vision_utills.preprocess.img_preprocessing import preprocess_bgr_letterbox, unletterbox_points
from pose_sensor_fusion.vision_utills.pose2d.pose_2d_postprocessing import decode_pose, pick_person, TrackState
from pose_sensor_fusion.vision_utills.visualize.visualize_pose import draw_pose_2d
from pose_sensor_fusion.utils.config_loader import load_yaml_config


def all_joints_visible_2d(kpts_640: Optional[np.ndarray], th: float) -> bool:
    if kpts_640 is None:
        return False
    conf = kpts_640.reshape(-1, 3)[:, 2]
    return bool(np.all(conf >= th))


def main_loop(cfg: Dict[str, Any]) -> None:
    engine_path = cfg["engine"]["path"]

    conf_th = float(cfg["inference"]["conf_th"])
    iou_th = float(cfg["inference"]["iou_th"])

    # 시각화용(그리기용) threshold:
    draw_kp_th = float(cfg["inference"]["kp_th"])

    # OK/NO 판정용 threshold: 더 엄격하게
    vis_th = 0.8

    hold_sec = float(cfg["tracking"]["hold_sec"])
    stick_iou = float(cfg["tracking"]["stick_iou"])

    rgb_w = int(cfg["stream"]["rgb"]["width"])
    rgb_h = int(cfg["stream"]["rgb"]["height"])
    fps = int(cfg["stream"]["fps"])

    trt_engine = TrtEngine(engine_path)
    st = TrackState()

    win_name = "pose_visibility_check"

    last_print_t = 0.0
    print_interval = 0.2  # 너무 많이 찍히면 0.2s마다 한 번만

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

                frame = np.ascontiguousarray(frame.copy())

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

                ok = all_joints_visible_2d(kpts_640, th=vis_th)

                # 콘솔 출력 (OK/NO 계속)
                t_now = time.time()
                if (t_now - last_print_t) >= print_interval:
                    if kpts_640 is None:
                        print("NO (no pose)")
                    else:
                        conf = kpts_640.reshape(-1, 3)[:, 2]
                        print(f"{'OK' if ok else 'NO'}  min={conf.min():.2f} mean={conf.mean():.2f} vis_th={vis_th:.2f}")
                    last_print_t = t_now

                # 시각화는 draw_kp_th(0.25) 기준으로 계속 그림
                disp = frame
                if kpts_640 is not None:
                    kpts_xy = unletterbox_points(kpts_640.reshape(-1, 3), scale, dx, dy)
                    draw_pose_2d(disp, kpts_xy, kp_th=draw_kp_th)

                cv2.putText(
                    disp,
                    f"{'OK' if ok else 'NO'} vis_th={vis_th:.2f} draw_th={draw_kp_th:.2f}",
                    (10, disp.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0) if ok else (0, 0, 255),
                    2,
                )

                cv2.imshow(win_name, disp)
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or key == ord("q"):
                    break

    finally:
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
    config_path = os.getenv("CONFIG_PATH", "configs/pose_sensor_fusion/run.yaml")
    cfg = load_yaml_config(config_path)
    main_loop(cfg)


if __name__ == "__main__":
    main()
