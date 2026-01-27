# import torch
# import torch.nn.functional as F
# from ultralytics.models.yolo.pose.train import PoseTrainer

# from utils.config import load_yaml

# from distill.teacher import load_teacher
# from distill.hooks import AttentionHook
# from distill.losses import kpt_distill_loss, attention_distill_loss

# '''
# Distill Pose Trainer 구현 핵심 코드
# '''
# class DistillPoseTrainer(PoseTrainer):
#     def __init__(self, *args, teacher_weight=None, hook_idx=22, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.distill_cfg = load_yaml("configs/distill_kpt.yaml")
        
#         # ⭐ teacher weight 꺼내기 (None 방지)
#         teacher_weight = self.distill_cfg["teacher"]["weight"]
#         assert teacher_weight is not None, "configs/distill_kpt.yaml의 teacher.weight가 None임"

#         # teacher
#         self.teacher = load_teacher(teacher_weight, self.device)
#         self.teacher.eval()

#         # attention hook
#         self.t_hook = AttentionHook()
#         self.s_hook = AttentionHook()

#         self.teacher.model[hook_idx].register_forward_hook(self.t_hook)
#         self.model.model[hook_idx].register_forward_hook(self.s_hook)
#         print("DISTILL CFG LOADED:", self.distill_cfg)

#     def loss(self, batch, preds=None):
#         # -----------------------------
#         # 기본 YOLO pose loss (GT)
#         # -----------------------------
#         loss, loss_items = super().loss(batch, preds)

#         imgs = batch["img"]

#         # -----------------------------
#         # teacher forward
#         # -----------------------------
#         with torch.no_grad():
#             t_preds = self.teacher(imgs)

#         # -----------------------------
#         # keypoint distillation
#         # -----------------------------
#         loss_kpt = F.mse_loss(
#             preds[0].keypoints.xy,
#             t_preds[0].keypoints.xy
#         )

#         # -----------------------------
#         # attention distillation
#         # -----------------------------
#         loss_att = F.mse_loss(
#             self.s_hook.att,
#             self.t_hook.att
#         )

#         # -----------------------------
#         # total loss
#         # -----------------------------
#         loss = loss + 0.3 * loss_kpt + 0.2 * loss_att

#         return loss, loss_items


import torch
import torch.nn.functional as F
from ultralytics.models.yolo.pose.train import PoseTrainer

from utils.config import load_yaml
from distill.teacher import load_teacher
from distill.hooks import AttentionHook


class DistillPoseTrainer(PoseTrainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # distill config
        self.distill_cfg = load_yaml("configs/distill_kpt.yaml")

        # hooks (아직 model 없음 → 여기선 생성만)
        self.t_hook = AttentionHook()
        self.s_hook = AttentionHook()

        # teacher는 미리 로드 가능
        teacher_weight = self.distill_cfg["teacher"]["weight"]
        self.teacher = load_teacher(teacher_weight, self.device)
        self.teacher.eval()

    def setup_model(self):
        # 🔥 여기서 student model이 실제로 생성됨
        super().setup_model()

        hook_idx = self.distill_cfg["hook"]["index"]

        # 이제는 self.model이 nn.Module임
        self.model.model[hook_idx].register_forward_hook(self.s_hook)
        self.teacher.model[hook_idx].register_forward_hook(self.t_hook)

        print(f"[Distill] Hooks registered at layer {hook_idx}")

    def loss(self, batch, preds=None):
        # 기본 YOLO loss
        loss, loss_items = super().loss(batch, preds)

        imgs = batch["img"]

        # teacher forward
        with torch.no_grad():
            t_preds = self.teacher(imgs)

        # keypoint distill
        loss_kpt = F.mse_loss(
            preds[0].keypoints.xy,
            t_preds[0].keypoints.xy
        )

        # attention distill
        loss_att = F.mse_loss(
            self.s_hook.att,
            self.t_hook.att
        )

        loss = (
            loss
            + self.distill_cfg["loss_weight"]["kpt"] * loss_kpt
            + self.distill_cfg["loss_weight"]["attention"] * loss_att
        )

        return loss, loss_items

    def on_train_end(self):
        super().on_train_end()
    
        best_ckpt = self.best
        assert best_ckpt is not None, "best.pt가 존재하지 않음"
    
        ckpt = torch.load(best_ckpt, map_location="cpu")
    
        student_state = ckpt["model"].state_dict()
    
        save_dir = Path(self.save_dir) / "clean_weights"
        save_dir.mkdir(parents=True, exist_ok=True)
    
        clean_path = save_dir / "student_best_clean.pt"
        torch.save(student_state, clean_path)
    
        print(f"✅ Clean BEST student weight saved at: {clean_path}")
