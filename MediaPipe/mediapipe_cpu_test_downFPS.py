# pose_realtime_tasks.py
import time
import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2

VIDEO_SOURCE = "/dev/video4"
MODEL_PATH = "./model/pose_landmarker_lite.task"  # 같은 폴더에 두기

def draw_landmarks_on_image(image_bgr, detection_result):
    if detection_result.pose_landmarks is None:
        return image_bgr

    annotated = image_bgr.copy()
    pose_landmarks_list = detection_result.pose_landmarks

    for pose_landmarks in pose_landmarks_list:
        landmark_proto = landmark_pb2.NormalizedLandmarkList()
        landmark_proto.landmark.extend([
            landmark_pb2.NormalizedLandmark(x=l.x, y=l.y, z=l.z, visibility=l.visibility)
            for l in pose_landmarks
        ])

        import mediapipe as mp
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
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(VIDEO_SOURCE)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 224)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 224)
    
    if not cap.isOpened():
        raise RuntimeError(f"카메라 열기 실패: {VIDEO_SOURCE}")

    prev_t = time.time()
    fps = 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
        out = draw_landmarks_on_image(frame, result)

        now = time.time()
        dt = now - prev_t
        prev_t = now
        if dt > 0:
            fps = 0.9 * fps + 0.1 * (1.0 / dt)

        cv2.putText(
            out,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

        cv2.imshow("MediaPipe Pose (Tasks)", out)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
