import torch
from pathlib import Path

# 1️⃣ distill 환경에서 best.pt 로드
best_pt = "runs/pose/train11/weights/best.pt"

ckpt = torch.load(best_pt, map_location="cpu")

# 2️⃣ student model state_dict만 추출
student_state = ckpt["model"].state_dict()

# 3️⃣ 새 clean pt로 저장
out_dir = Path("weights/export")
out_dir.mkdir(parents=True, exist_ok=True)

clean_pt = out_dir / "yolo11n_pose21_clean.pt"
torch.save(student_state, clean_pt)

print(f"✅ Clean weight extracted: {clean_pt}")