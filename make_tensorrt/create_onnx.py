from ultralytics import YOLO

m = YOLO("yolo11n-pose.pt")
m.export(format="onnx", imgsz=640, simplify=False, opset=17)

