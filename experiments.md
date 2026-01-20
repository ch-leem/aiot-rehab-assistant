## Experiment Log

### Step 01 - Dataset Filtering
- COCO train/val filtered based on keypoint visibility
- HICO full-body samples selected

### Step 02 - MMpose Labeling
- RTMDet + MMPose
- Output: COCO-style keypoints JSON

### Step 03 - YOLO-M Training
- Teacher model trained with generated keypoints

### Step 04 - YOLO-N Distillation
- Feature + logit distillation