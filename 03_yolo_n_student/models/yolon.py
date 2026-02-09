from ultralytics import YOLO

def load_student(cfg_path, device):
    model = YOLO(cfg_path)
    model.model.to(device)
    return model
