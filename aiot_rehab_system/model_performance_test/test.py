#!/usr/bin/env python3
import os
import glob
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from tqdm import tqdm

import cv2
import numpy as np
import yaml

# 네 프로젝트 코드 사용 (경로 맞춰 수정)
from pose_sensor_fusion.vision_utills.inference.trt_engine import TrtEngine
from pose_sensor_fusion.vision_utills.preprocess.img_preprocessing import preprocess_bgr_letterbox, unletterbox_points
from pose_sensor_fusion.vision_utills.pose2d.pose_2d_postprocessing import decode_pose


# -------------------------
# Data loading (YOLO pose txt)
# -------------------------

@dataclass
class GTObj:
    bbox_xywh: np.ndarray        # (4,) in pixels on original image: x,y,w,h
    kpts_xyv: np.ndarray         # (K,3) x,y,v in pixels on original image
    cls: int

def _read_yolo_pose_label_txt(label_path: str, img_w: int, img_h: int, k: int) -> List[GTObj]:
    gts: List[GTObj] = []
    if not os.path.isfile(label_path):
        return gts

    with open(label_path, "r") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            parts = s.split()
            # expected: 1 + 4 + K*3
            need = 1 + 4 + k * 3
            if len(parts) != need:
                # skip malformed line
                continue

            cls = int(float(parts[0]))
            cx, cy, bw, bh = map(float, parts[1:5])
            # normalized -> pixels
            cx *= img_w
            cy *= img_h
            bw *= img_w
            bh *= img_h
            x = cx - bw / 2.0
            y = cy - bh / 2.0

            kp = np.array(list(map(float, parts[5:])), dtype=np.float32).reshape(k, 3)
            kp[:, 0] *= img_w
            kp[:, 1] *= img_h
            # kp[:,2] is v (0,1,2) already, keep as is

            gts.append(GTObj(
                bbox_xywh=np.array([x, y, bw, bh], dtype=np.float32),
                kpts_xyv=kp,
                cls=cls,
            ))
    return gts


# -------------------------
# OKS + AP
# -------------------------

def _oks(pred_xy: np.ndarray, gt_xyv: np.ndarray, area: float, sigmas: np.ndarray) -> float:
    """
    pred_xy: (K,2) predicted keypoints in pixels
    gt_xyv : (K,3) GT in pixels with visibility v in {0,1,2}
    area   : object area in pixels^2 (use bbox area)
    sigmas : (K,) per-keypoint sigma
    """
    if area <= 1.0:
        area = 1.0
    vars_ = (sigmas * 2.0) ** 2  # COCO style denominator term

    gt_xy = gt_xyv[:, :2]
    v = gt_xyv[:, 2]

    # visibility mask: v > 0 means labeled/visible in COCO sense
    m = v > 0
    if not np.any(m):
        return 0.0

    dx = pred_xy[m, 0] - gt_xy[m, 0]
    dy = pred_xy[m, 1] - gt_xy[m, 1]
    e = (dx * dx + dy * dy) / (vars_[m] * (area + 1e-9) * 2.0)
    return float(np.mean(np.exp(-e)))

def _match_image(
    preds: List[Tuple[float, np.ndarray]],   # list of (score, pred_kpts_xy) for one image
    gts: List[GTObj],
    oks_thr: float,
    sigmas: np.ndarray
) -> Tuple[List[int], List[int]]:
    """
    Returns lists:
      tp_flags aligned with preds order, 1 if TP else 0
      fp_flags aligned with preds order, 1 if FP else 0
    Matching rule: greedy by score descending, match to highest OKS GT not already matched if OKS >= thr.
    """
    if len(preds) == 0:
        return [], []
    if len(gts) == 0:
        return [0] * len(preds), [1] * len(preds)

    gt_used = [False] * len(gts)
    tp = [0] * len(preds)
    fp = [0] * len(preds)

    for i, (sc, pk) in enumerate(preds):
        best_j = -1
        best_oks = -1.0
        for j, gt in enumerate(gts):
            if gt_used[j]:
                continue
            area = float(gt.bbox_xywh[2] * gt.bbox_xywh[3])
            oks = _oks(pk, gt.kpts_xyv, area=area, sigmas=sigmas)
            if oks > best_oks:
                best_oks = oks
                best_j = j
        if best_j >= 0 and best_oks >= oks_thr:
            tp[i] = 1
            gt_used[best_j] = True
        else:
            fp[i] = 1

    return tp, fp

def _ap_from_pr(rec: np.ndarray, prec: np.ndarray) -> float:
    """
    101-point interpolation AP (COCO style-ish)
    """
    if rec.size == 0:
        return 0.0

    # make precision non-increasing
    mpre = np.maximum.accumulate(prec[::-1])[::-1]
    # sample at 101 recall thresholds
    rs = np.linspace(0.0, 1.0, 101)
    p_at_r = np.interp(rs, rec, mpre, left=0.0, right=mpre[-1])
    return float(np.mean(p_at_r))

def _compute_ap(
    all_preds: List[Tuple[str, float, np.ndarray]],  # (img_key, score, pred_kpts_xy)
    gt_map: Dict[str, List[GTObj]],
    oks_thr: float,
    sigmas: np.ndarray
) -> Tuple[float, float, float]:
    """
    Compute AP at one oks threshold.
    Returns: (AP, Precision_at_end, Recall_at_end)
    Precision/Recall here are final values after processing all detections.
    """
    # sort predictions by score descending
    all_preds = sorted(all_preds, key=lambda x: x[1], reverse=True)

    # total GT count (only those with at least 1 labeled kp)
    total_gt = 0
    for gts in gt_map.values():
        for gt in gts:
            if np.any(gt.kpts_xyv[:, 2] > 0):
                total_gt += 1

    if total_gt == 0:
        return 0.0, 0.0, 0.0

    # group preds per image in sorted order (we need greedy matching by score globally, but matching is per-image)
    # We'll process globally and keep per-image matched flags by storing gt_used sets.
    gt_used_map: Dict[str, List[bool]] = {k: [False] * len(v) for k, v in gt_map.items()}

    tp_list = []
    fp_list = []

    for img_key, sc, pk in all_preds:
        gts = gt_map.get(img_key, [])
        if len(gts) == 0:
            tp_list.append(0)
            fp_list.append(1)
            continue

        gt_used = gt_used_map[img_key]
        best_j = -1
        best_oks = -1.0
        for j, gt in enumerate(gts):
            if gt_used[j]:
                continue
            area = float(gt.bbox_xywh[2] * gt.bbox_xywh[3])
            oks = _oks(pk, gt.kpts_xyv, area=area, sigmas=sigmas)
            if oks > best_oks:
                best_oks = oks
                best_j = j

        if best_j >= 0 and best_oks >= oks_thr:
            tp_list.append(1)
            fp_list.append(0)
            gt_used[best_j] = True
        else:
            tp_list.append(0)
            fp_list.append(1)

    tp = np.array(tp_list, dtype=np.float32)
    fp = np.array(fp_list, dtype=np.float32)

    tp_cum = np.cumsum(tp)
    fp_cum = np.cumsum(fp)

    rec = tp_cum / (total_gt + 1e-9)
    prec = tp_cum / (tp_cum + fp_cum + 1e-9)

    ap = _ap_from_pr(rec, prec)
    p_end = float(prec[-1]) if prec.size else 0.0
    r_end = float(rec[-1]) if rec.size else 0.0
    return ap, p_end, r_end


# -------------------------
# Main evaluator
# -------------------------

def eval_pose_trt_custom(
    engine_path: str,
    data_yaml: str,
    imgsz: int = 640,
    conf_th: float = 0.25,
    iou_th: float = 0.45,
    kp_th: float = 0.25,
    max_images: Optional[int] = None,
    # OKS sigmas: dataset-dependent. If you don't have your own, start with 0.05 for all.
    sigmas: Optional[List[float]] = None
) -> Dict[str, object]:

    with open(data_yaml, "r") as f:
        d = yaml.safe_load(f)

    root = d["path"]
    val_images_rel = d["val"]
    kpt_shape = d["kpt_shape"]
    k = int(kpt_shape[0])

    val_img_dir = os.path.join(root, val_images_rel)
    val_label_dir = val_img_dir.replace("/images", "/labels")

    img_paths = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"):
        img_paths.extend(glob.glob(os.path.join(val_img_dir, ext)))
    img_paths = sorted(img_paths)
    if max_images is not None:
        img_paths = img_paths[:max_images]

    if sigmas is None:
        sigmas_arr = np.full((k,), 1.0 / k, dtype=np.float32)
    else:
        if len(sigmas) != k:
            raise ValueError(f"sigmas length must be {k}, got {len(sigmas)}")
        sigmas_arr = np.array(sigmas, dtype=np.float32)

    trt = TrtEngine(engine_path)

    gt_map: Dict[str, List[GTObj]] = {}
    all_preds: List[Tuple[str, float, np.ndarray]] = []

    infer_ms_list: List[float] = []

    for img_path in tqdm(img_paths, desc="TRT Pose Eval", unit="img"):
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]

        base = os.path.splitext(os.path.basename(img_path))[0]
        label_path = os.path.join(val_label_dir, base + ".txt")

        gts = _read_yolo_pose_label_txt(label_path, img_w=w, img_h=h, k=k)
        img_key = base
        gt_map[img_key] = gts

        # preprocess (letterbox) -> TRT infer
        inp, scale, dx, dy = preprocess_bgr_letterbox(img, imgsz)

        t0 = time.perf_counter()
        out = trt.infer(inp)
        t1 = time.perf_counter()
        infer_ms_list.append((t1 - t0) * 1000.0)

        boxes, scores, kpts_640 = decode_pose(out, conf_th=conf_th, iou_th=iou_th)

        if boxes.shape[0] == 0:
            continue

        # collect predictions for AP: keep all detections >= conf_th
        for i in range(boxes.shape[0]):
            sc = float(scores[i])
            if sc < conf_th:
                continue

            kp = kpts_640[i]  # (K,3) on 640 letterbox canvas, usually x,y,score
            # convert to original image pixel coords
            kp_xyv = unletterbox_points(kp.reshape(-1, 3), scale, dx, dy).reshape(k, 3)
            pred_xy = kp_xyv[:, :2].astype(np.float32)

            all_preds.append((img_key, sc, pred_xy))

    trt.close()

    # AP50 and AP50-95
    oks_thrs = [0.50 + 0.05 * i for i in range(10)]  # 0.50..0.95
    ap_list = []
    p50 = 0.0
    r50 = 0.0

    for t in oks_thrs:
        ap, p_end, r_end = _compute_ap(all_preds, gt_map, oks_thr=t, sigmas=sigmas_arr)
        ap_list.append(ap)
        if abs(t - 0.50) < 1e-9:
            p50 = p_end
            r50 = r_end

    return {
        "model": engine_path,
        "pose_mAP50": float(ap_list[0]) if ap_list else 0.0,
        "pose_mAP50_95": float(np.mean(ap_list)) if ap_list else 0.0,
        # Ultralytics mp/mr과 정의가 1:1 동일하진 않지만,
        # 일반적으로 “OKS=0.50 기준 최종 precision/recall”로 두면 비교 지표로 유용함.
        "pose_P": float(p50),
        "pose_R": float(r50),
        "inference_ms": float(np.mean(infer_ms_list)) if infer_ms_list else None,
        "num_images": len(img_paths),
        "num_preds": len(all_preds),
    }


if __name__ == "__main__":
    out = eval_pose_trt_custom(
        engine_path="/home/a203/workspace/S14P11A203/aiot_rehab_system/models/yolo11n-pose21_fp16.engine",
        data_yaml="/home/a203/workspace/S14P11A203/aiot_rehab_system/test/yolo_data.yaml",
        imgsz=640,
        conf_th=0.25,
        iou_th=0.45,
        kp_th=0.25,
        max_images=None,   # 빠르게 확인하려면 50 같은 숫자 추천
        sigmas=None        # 없으면 0.05로 통일, 필요하면 21개 리스트로 넣기
    )
    print(out)
