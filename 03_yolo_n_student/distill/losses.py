# distill/losses.py
import torch.nn.functional as F

def feature_distill_loss(s_feats, t_feats, feat_weights):
    """
    s_feats, t_feats: dict {p3, p4, p5}
    feat_weights: dict {p3, p4, p5}
    """
    loss = 0.0
    for k in feat_weights.keys():
        fs = s_feats[k]
        ft = t_feats[k].detach()
        loss += feat_weights[k] * F.smooth_l1_loss(fs, ft)
    return loss


def kpt_distill_loss(s_kpt, t_kpt, gt_kpt, alpha=0.6):
    """
    GT + teacher 혼합
    """
    target = alpha * t_kpt + (1 - alpha) * gt_kpt
    return F.smooth_l1_loss(s_kpt, target)
