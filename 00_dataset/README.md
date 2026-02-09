## Dataset Preparation

YOLO 모델 학습을 위한 Dataset 을 구축하고 필터링하기 위한 scripts 파일을 정의한 폴더입니다.

### Not included in git
- raw datasets (COCO, HICO)
- processed annotations
- extracted images


### Workflow
1. Run filtering scripts in `scripts/`
2. Generate image list txt files
3. Extract images into `input_images/`

### Dataset



### Folder Structure
```
00_dataset
|- scripts
|- input_images
|- outputs
|- train2017  # coco train dataset
|- val2017 # coco valid dataset
|- hico/images # hico dataset
|- annotations_trainval2017/annotations # coco dataset annotations
|- annotations_hico/annotations

```
- 다운로드 받은 파일 그대로 사용합니다.