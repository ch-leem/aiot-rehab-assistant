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
from distill.hooks import MultiScaleFeatureHook, NamedFeatureHook
from distill.losses import feature_distill_loss, kpt_distill_loss


class DistillPoseTrainer(PoseTrainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # distill config
        self.distill_cfg = load_yaml("configs/distill_kpt.yaml")

        # # hooks (아직 model 없음 → 여기선 생성만)
        # self.t_hook = AttentionHook()
        # self.s_hook = AttentionHook()

        # teacher는 미리 로드 가능
        teacher_weight = self.distill_cfg["teacher"]["weight"]
        self.teacher = load_teacher(teacher_weight, self.device)
        self.teacher.eval()

    def setup_model(self):
        super().setup_model()
    
        self.t_feat_hook = MultiScaleFeatureHook()
        self.s_feat_hook = MultiScaleFeatureHook()
    
        feat_layers = self.distill_cfg["hook"]["features"]  # {"p3":16,"p4":19,"p5":22}
    
        self._hook_handles = []
        for name, idx in feat_layers.items():
            h1 = self.model.model[idx].register_forward_hook(
                NamedFeatureHook(self.s_feat_hook, name)
            )
            h2 = self.teacher.model[idx].register_forward_hook(
                NamedFeatureHook(self.t_feat_hook, name)
            )
            self._hook_handles.extend([h1, h2])
    
        print(f"[Distill] Feature hooks registered: {feat_layers}")


    def loss(self, batch, preds=None):
        base_loss, loss_items = super().loss(batch, preds)
    
        imgs = batch["img"]
        gt_kpt = batch["keypoints"][..., :2]  # (x,y)
    
        with torch.no_grad():
            t_preds = self.teacher(imgs)
    
        loss = base_loss
    
        # feature distill
        if self.distill_cfg["distill"]["use_feat"]:
            loss_feat = feature_distill_loss(
                self.s_feat_hook.features,
                self.t_feat_hook.features,
                self.distill_cfg["loss_weight"]["feat"]
            )
            loss = loss + loss_feat
    
        # keypoint distill
        if self.distill_cfg["distill"]["use_kpt"]:
            loss_kpt = kpt_distill_loss(
                preds[0].keypoints.xy,
                t_preds[0].keypoints.xy,
                gt_kpt,
                alpha=0.6
            )
            loss = loss + self.distill_cfg["loss_weight"]["kpt"] * loss_kpt
    
        return loss, loss_items


    def on_train_end(self):
        # 🔥 hook 제거 (pickle 에러 방지)
        if hasattr(self, "_hook_handles"):
            for h in self._hook_handles:
                h.remove()
                
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
