import time
import threading
import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = "./model/pose_landmarker_full.task"
DEV = 4  # /dev/video4
W, H, FPS = 640, 480, 30   # 필요하면 424x240 같은 더 작은 값 추천

# ---- 전역: 최신 결과만 저장 (지연 제거 핵심) ----
latest_result = None
latest_ts_ms = -1
lock = threading.Lock()

# MediaPipe Pose connections (33개 기준)
POSE_CONNECTIONS = mp.solutions.pose.POSE_CONNECTIONS

def result_cb(result: vision.PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global latest_result, latest_ts_ms
    with lock:
        # 오래된 결과는 버림
        if timestamp_ms >= latest_ts_ms:
            latest_result = result
            latest_ts_ms = timestamp_ms

def draw_fast(image_bgr, result):
    """drawing_utils 대신 OpenCV로 가볍게"""
    if result is None or not result.pose_landmarks:
        return image_bgr

    out = image_bgr
    H_, W_ = out.shape[:2]
    lms = result.pose_landmarks[0]  # num_poses=1

    # 점
    for lm in lms:
        u = int(lm.x * W_)
        v = int(lm.y * H_)
        if 0 <= u < W_ and 0 <= v < H_:
            cv2.circle(out, (u, v), 2, (0, 255, 0), -1)

    # 선
    for a, b in POSE_CONNECTIONS:
        pa = lms[a]
        pb = lms[b]
        ua, va = int(pa.x * W_), int(pa.y * H_)
        ub, vb = int(pb.x * W_), int(pb.y * H_)
        if 0 <= ua < W_ and 0 <= va < H_ and 0 <= ub < W_ and 0 <= vb < H_:
            cv2.line(out, (ua, va), (ub, vb), (0, 255, 0), 1)

    return out

def gstreamer_source(dev=4, w=640, h=480, fps=30):
    # v4l2src + appsink drop=true 로 지연 방지
    return (
        f"v4l2src device=/dev/video{dev} ! "
        f"video/x-raw, width={w}, height={h}, framerate={fps}/1 ! "
        f"videoconvert ! "
        f"appsink drop=true max-buffers=1 sync=false"
    )

def main():
    # ---- MediaPipe Tasks: LIVE_STREAM + async ----
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.LIVE_STREAM,
        num_poses=1,
        result_callback=result_cb,
        # lite 모델이면 기본으로도 OK, 필요시 confidence 조절 가능
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    # ---- 캡처: GStreamer 권장 ----
    cap = cv2.VideoCapture(gstreamer_source(DEV, W, H, FPS), cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        # fallback: 일반 v4l2
        cap = cv2.VideoCapture(f"/dev/video{DEV}", cv2.CAP_V4L2)

    if not cap.isOpened():
        raise RuntimeError(f"카메라 열기 실패: /dev/video{DEV}")

    fps_ema = 0.0
    last = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # 가능하면 입력을 더 줄이면 FPS 크게 개선됨:
        # frame_small = cv2.resize(frame, (320, 240))
        # 여기선 카메라 자체를 640x480로 맞추는 걸 권장
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        ts_ms = int(time.time() * 1000)
        landmarker.detect_async(mp_image, ts_ms)

        # 최신 결과를 받아서 그리기 (없으면 그냥 원본)
        with lock:
            res = latest_result

        out = draw_fast(frame, res)

        now = time.time()
        dt = now - last
        last = now
        if dt > 0:
            fps_ema = 0.9 * fps_ema + 0.1 * (1.0 / dt)

        cv2.putText(out, f"FPS: {fps_ema:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        cv2.imshow("MediaPipe Pose (Tasks, low-latency)", out)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q") or k == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()

if __name__ == "__main__":
    main()
