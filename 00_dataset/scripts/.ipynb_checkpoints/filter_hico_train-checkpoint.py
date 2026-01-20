import json
import os

"""
HICO-DET annotation 기반
- 전신 인물이 잘 나왔을 확률이 높은 이미지 필터링
- 출력: MM Pose 입력용 이미지 리스트
"""

# =========================
# 필터 기준 (튜닝 가능)
# =========================
MIN_BBOX_RATIO = 0.15      # bbox_area / image_area
MAX_PEOPLE = 2

MIN_ASPECT_RATIO = 0.35   # w / h
MAX_ASPECT_RATIO = 0.75

TOP_MARGIN = 0.05         # 머리 잘림 방지
BOTTOM_MARGIN = 0.95      # 발 잘림 방지


def is_fullbody_person(bbox, img_w, img_h):
    x, y, w, h = bbox
    bbox_area = w * h
    img_area = img_w * img_h

    # bbox 크기
    if bbox_area / img_area < MIN_BBOX_RATIO:
        return False

    # 종횡비 (전신 비율)
    aspect = w / h
    if not (MIN_ASPECT_RATIO <= aspect <= MAX_ASPECT_RATIO):
        return False

    # 머리 / 발 잘림 방지
    top = y / img_h
    bottom = (y + h) / img_h

    if top < TOP_MARGIN:
        return False
    if bottom > BOTTOM_MARGIN:
        return False

    return True


def filter_hico_annotations(hico_json, image_root, output_dir="outputs"):
    with open(hico_json, "r") as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    selected = []

    for entry in data:
        file_name = entry["file_name"]
        img_path = os.path.join(image_root, file_name)

        if not os.path.exists(img_path):
            continue

        # HICO 이미지 크기 (고정: COCO 기반)
        img_w, img_h = 640, 480

        persons = [
            ann for ann in entry["annotations"]
            if ann["category_id"] == 1
        ]

        if not (1 <= len(persons) <= MAX_PEOPLE):
            continue

        valid_persons = 0
        for p in persons:
            if is_fullbody_person(p["bbox"], img_w, img_h):
                valid_persons += 1

        if valid_persons >= 1:
            selected.append({
                "file_name": file_name,
                "num_person": len(persons),
                "valid_fullbody_person": valid_persons
            })

    # 결과 저장
    with open(f"{output_dir}/hico_fullbody_candidates.json", "w") as f:
        json.dump(selected, f, indent=2)

    with open(f"{output_dir}/openpose_image_list_hico.txt", "w") as f:
        for s in selected:
            f.write(os.path.join(image_root, s["file_name"]) + "\n")

    print(f"✔ 전신 후보 이미지 수: {len(selected)}")
    print("✔ hico_fullbody_candidates.json 생성")
    print("✔ openpose_image_list_hico.txt 생성")


if __name__ == "__main__":
    HICO_JSON = "annotations_hico/annotations/trainval_hico.json"   # 실제 파일명으로 수정
    IMAGE_ROOT = "hico/images/train2015/"

    filter_hico_annotations(HICO_JSON, IMAGE_ROOT)
