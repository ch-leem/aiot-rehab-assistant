import torch.nn.functional as F

def kpt_distill_loss(s_kpt, t_kpt):
    return F.mse_loss(s_kpt, t_kpt)

def attention_distill_loss(s_att, t_att):
    return F.mse_loss(s_att, t_att)
