from dataclasses import dataclass
from typing import Optional
import numpy as np


# =========================
# YOLO Pose postprocess (Ultralytics style)
# output: (1,56,8400)
#  0:4 bbox cxcywh on 640
#  4   obj conf
#  5:56 keypoints (17*3) x,y,score on 640
# =========================
def nms_xywh(boxes_xywh: np.ndarray, scores: np.ndarray, iou_th: float) -> np.ndarray:
    cx, cy, w, h = boxes_xywh[:, 0], boxes_xywh[:, 1], boxes_xywh[:, 2], boxes_xywh[:, 3]
    x1 = cx - w / 2
    y1 = cy - h / 2
    x2 = cx + w / 2
    y2 = cy + h / 2
    areas = (x2 - x1) * (y2 - y1)

    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        iw = np.maximum(0.0, xx2 - xx1)
        ih = np.maximum(0.0, yy2 - yy1)
        inter = iw * ih
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        inds = np.where(iou <= iou_th)[0]
        order = order[inds + 1]
    return np.array(keep, dtype=np.int32)

# def decode_pose(output: np.ndarray, conf_th: float = 0.25, iou_th: float = 0.45):
#     pred = output[0].transpose(1, 0)  # (8400,56)
#     boxes = pred[:, 0:4]
#     obj = pred[:, 4]
#     kpts = pred[:, 5:].reshape(-1, 17, 3)

#     m = obj >= conf_th
#     boxes = boxes[m]
#     obj = obj[m]
#     kpts = kpts[m]

#     if boxes.shape[0] == 0:
#         return np.zeros((0, 4), np.float32), np.zeros((0,), np.float32), np.zeros((0, 17, 3), np.float32)

#     keep = nms_xywh(boxes, obj, iou_th)
#     return boxes[keep], obj[keep], kpts[keep]

def decode_pose(output: np.ndarray, conf_th: float = 0.25, iou_th: float = 0.45, nc: int = 1):
    # output0: (1, C, N) where C = 4 + nc + kpt_num*3
    pred = output[0].transpose(1, 0)  # (N, C)

    C = pred.shape[1]
    kpt_dim = 3
    kpt_num = (C - 4 - nc) // kpt_dim
    if 4 + nc + kpt_num * kpt_dim != C:
        raise ValueError(f"Unexpected output channels C={C}, expected 4+nc+kpt_num*3. nc={nc}")

    boxes = pred[:, 0:4]

    # class score (nc=1이면 그냥 pred[:,4])
    cls = pred[:, 4:4 + nc]
    scores = cls.max(axis=1)

    kpt_start = 4 + nc
    kpts = pred[:, kpt_start:].reshape(-1, kpt_num, kpt_dim)

    m = scores >= conf_th
    boxes = boxes[m]
    scores = scores[m]
    kpts = kpts[m]

    if boxes.shape[0] == 0:
        return (
            np.zeros((0, 4), np.float32),
            np.zeros((0,), np.float32),
            np.zeros((0, kpt_num, kpt_dim), np.float32),
        )

    keep = nms_xywh(boxes, scores, iou_th)
    return boxes[keep], scores[keep], kpts[keep]


def iou_xywh(a: np.ndarray, b: np.ndarray) -> float:
    ax1, ay1 = a[0] - a[2] / 2, a[1] - a[3] / 2
    ax2, ay2 = a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1 = b[0] - b[2] / 2, b[1] - b[3] / 2
    bx2, by2 = b[0] + b[2] / 2, b[1] + b[3] / 2

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
    inter = iw * ih
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter + 1e-9)

@dataclass
class TrackState:
    bbox: Optional[np.ndarray] = None
    kpts_640: Optional[np.ndarray] = None
    last_seen: float = 0.0

def pick_person(boxes: np.ndarray, scores: np.ndarray, kpts: np.ndarray, st: TrackState, stick_iou: float = 0.2):
    if boxes.shape[0] == 0:
        return None

    if st.bbox is None:
        i = int(scores.argmax())
        return boxes[i], float(scores[i]), kpts[i]

    ious = np.array([iou_xywh(st.bbox, b) for b in boxes], dtype=np.float32)
    best = int(ious.argmax())
    if float(ious[best]) >= stick_iou:
        return boxes[best], float(scores[best]), kpts[best]

    i = int(scores.argmax())
    return boxes[i], float(scores[i]), kpts[i]