import time
import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2

CAM_INDEX = 4
MODEL_PATH = "./model/pose_landmarker_lite.task"

WIDTH, HEIGHT = 640, 360
INFER_EVERY_N = 2
GRAB_DROP_N = 2

latest_result = None
latest_ts = 0

def cb(result: vision.PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global latest_result, latest_ts
    latest_result = result
    latest_ts = timestamp_ms

def draw_pose(image_bgr, detection_result):
    if detection_result is None or not detection_result.pose_landmarks:
        return image_bgr

    annotated = image_bgr.copy()

    for pose_landmarks in detection_result.pose_landmarks:
        landmark_proto = landmark_pb2.NormalizedLandmarkList()
        landmark_proto.landmark.extend([
            landmark_pb2.NormalizedLandmark(
                x=l.x, y=l.y, z=l.z,
                visibility=(l.visibility if l.visibility is not None else 0.0)
            )
            for l in pose_landmarks
        ])

        mp.solutions.drawing_utils.draw_landmarks(
            annotated,
            landmark_proto,
            mp.solutions.pose.POSE_CONNECTIONS,
            mp.solutions.drawing_styles.get_default_pose_landmarks_style()
        )

    return annotated

def main():
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.LIVE_STREAM,
        result_callback=cb,
        num_poses=1
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"Camera open failed: index={CAM_INDEX}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    prev_t = time.time()
    fps = 0.0
    frame_i = 0

    while True:
        for _ in range(GRAB_DROP_N):
            cap.grab()

        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        if frame_i % INFER_EVERY_N == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int(time.time() * 1000)
            landmarker.detect_async(mp_image, ts_ms)
        frame_i += 1

        # print(latest_result)
        # if(latest_result is not None):
        #     print(type(latest_result))
        #     assert False, "latest_result is None"

        out = draw_pose(frame, latest_result)

        now = time.time()
        dt = now - prev_t
        prev_t = now
        if dt > 0:
            fps = 0.9 * fps + 0.1 * (1.0 / dt)

        cv2.putText(out, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(out, f"Result ts: {latest_ts}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("MediaPipe Pose (low-latency + draw)", out)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
