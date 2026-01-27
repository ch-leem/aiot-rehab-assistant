from ultralytics import YOLO
import torch

# 1️⃣ 모델 구조 먼저 생성 (공식 nano pose 모델)
model = YOLO("configs/yolo11n-pose.yaml")  
# ↑ 이건 '구조용' (kpt head 포함)

# 2️⃣ clean weight 로드 (state_dict)
state_dict = torch.load(
    "weights/export/yolo11n_pose21_clean.pt",
    map_location="cpu"
)

model.model.load_state_dict(state_dict, strict=True)

print("✅ clean weight loaded into YOLO model")

# 3️⃣ ONNX export
model.export(
    format="onnx",
    imgsz=640,
    opset=17,
    simplify=False
)

print("✅ ONNX export done")
