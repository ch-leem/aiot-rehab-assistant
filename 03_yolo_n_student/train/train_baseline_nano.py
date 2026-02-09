'''
YOLO11 nano model baseline train
'''

from ultralytics import YOLO

model = YOLO("configs/yolo11n-pose.yaml")

model.train(
    data="configs/data.yaml",
    imgsz=640,
    batch=16,
    epochs=50,
    device=8,
    project="../runs/pose",
    name="nano_baseline_21kp",
)
