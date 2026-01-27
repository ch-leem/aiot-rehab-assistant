from ultralytics import YOLO

def load_teacher(weight_path, device):
    model = YOLO(weight_path).model.to(device)
    model.eval()
    for p in model.parameters():
        p.requires_grad = False
    return model