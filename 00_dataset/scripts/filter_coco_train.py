import json
import os
from collections import defaultdict

"""
COCO train2017 annotation 기반
- MM Pose로 toe/heel까지 안정적으로 찍을 수 있는 이미지 필터링
- 출력: image_id / file_name 리스트
"""

# =========================
# 설정값 (프로젝트 목적에 맞게 튜닝)
# =========================
MIN_NUM_KEYPOINTS = 8        # num_keypoints 기준
MIN_VISIBLE_KPS = 8          # visible (v==2) keypoints 수
MIN_BBOX_RATIO = 0.08        # bbox / image area
MAX_PERSON_PER_IMAGE = 3     # 너무 혼잡한 이미지 제거
REQUIRE_ANKLE = True         # 발목 필수 (OpenPose 발 확장 전제)

# COCO ankle index
LEFT_ANKLE = 15
RIGHT_ANKLE = 16


# =========================
# 핵심 판별 함수 (annotation 단위)
# =========================
def is_pose_candidate_annotation(ann, img_w, img_h):
    # person only
    if ann["category_id"] != 1:
        return False

    # crowd 제거
    if ann.get("iscrowd", 0) == 1:
        return False

    # 최소 keypoint 수
    if ann["num_keypoints"] < MIN_NUM_KEYPOINTS:
        return False

    keypoints = ann["keypoints"]

    # visible keypoints 수
    visible_cnt = sum(
        1 for i in range(2, len(keypoints), 3)
        if keypoints[i] == 2
    )
    if visible_cnt < MIN_VISIBLE_KPS:
        return False

    # bbox 크기
    x, y, w, h = ann["bbox"]
    bbox_area = w * h
    img_area = img_w * img_h
    if bbox_area / img_area < MIN_BBOX_RATIO:
        return False

    # 발목 필수 (OpenPose toe/heel 확장 전제)
    if REQUIRE_ANKLE:
        left_ankle_visible = keypoints[LEFT_ANKLE * 3 + 2] == 2
        right_ankle_visible = keypoints[RIGHT_ANKLE * 3 + 2] == 2
        if not (left_ankle_visible or right_ankle_visible):
            return False

    return True


# =========================
# 이미지 단위 필터링
# =========================
def filter_images(coco_json_path, image_root):
    with open(coco_json_path, "r") as f:
        coco = json.load(f)

    images = {img["id"]: img for img in coco["images"]}
    anns_by_img = defaultdict(list)

    for ann in coco["annotations"]:
        anns_by_img[ann["image_id"]].append(ann)

    selected = []

    for img_id, anns in anns_by_img.items():
        img = images[img_id]
        img_w, img_h = img["width"], img["height"]

        valid_persons = 0

        for ann in anns:
            if is_pose_candidate_annotation(ann, img_w, img_h):
                valid_persons += 1

        if 1 <= valid_persons <= MAX_PERSON_PER_IMAGE:
            selected.append({
                "image_id": img_id,
                "file_name": img["file_name"],
                "width": img_w,
                "height": img_h,
                "num_valid_person": valid_persons
            })

    return selected


# =========================
# 실행부
# =========================
if __name__ == "__main__":
    COCO_JSON = "annotations_trainval2017/annotations/person_keypoints_train2017.json"
    IMAGE_ROOT = "train2017/"

    results = filter_images(COCO_JSON, IMAGE_ROOT)

    print(f"총 선택된 이미지 수: {len(results)}")

    # 결과 저장
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/coco_train_pose_candidates.json", "w") as f:
        json.dump(results, f, indent=2)

    # MM Pose 입력용 txt
    with open("outputs/coco_train_image_list.txt", "w") as f:
        for r in results:
            f.write(os.path.join(IMAGE_ROOT, r["file_name"]) + "\n")

    print("✔ coco_train_pose_candidates.json 생성 완료")
    print("✔ coco_train_image_list.txt 생성 완료")
