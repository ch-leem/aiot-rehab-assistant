import os
import shutil

txt_path = "../coco_train_image_list.txt"  # 경로 목록 txt
'''
txt list
coco_train_imge_list.txt
coco_val_image_list.txt
hico_image_list.txt
'''
output_dir = "input_images"     # 복사할 폴더

os.makedirs(output_dir, exist_ok=True)

with open(txt_path, "r") as f:
    paths = [line.strip() for line in f if line.strip()]

copied = 0
missing = 0

for src_path in paths:
    if not os.path.isfile(src_path):
        missing += 1
        continue

    filename = os.path.basename(src_path)
    dst_path = os.path.join(output_dir, filename)

    shutil.copy2(src_path, dst_path)
    copied += 1

print(f"복사 완료: {copied}개")
print(f"경로 없음: {missing}개")
