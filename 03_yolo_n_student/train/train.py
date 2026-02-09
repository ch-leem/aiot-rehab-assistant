from ultralytics.cfg import get_cfg
from train.distill_trainer import DistillPoseTrainer
from utils.seed import set_seed
import torch
torch.cuda.set_device(0)

set_seed(42)

cfg = get_cfg()

cfg.task = "pose"
cfg.model = "weights/student/yolo11n-pose.pt"
cfg.data = "configs/data.yaml"
cfg.imgsz = 640
cfg.batch = 16
cfg.epochs = 50
cfg.device = "cuda"

trainer = DistillPoseTrainer(
    cfg=cfg
    # teacher_weight="weights/teacher/yolom_kpt.pt",
    # hook_idx=22
)

trainer.train()
