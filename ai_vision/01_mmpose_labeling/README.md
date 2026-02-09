# MMpose Data Labeling
MM pose 모델을 기반으로 포즈 라벨링 파이프라인을 구현한 디렉토리입니다.

## Overview
- Person detection: RTMDet (MMDetection)
- Pose estimation: MMpose (Top-down)
- Output: COCO-style keypoint annotations

## Directory Structure
```
configs/ Model configuration and checkpoint paths
scripts/ Executable pose inference and visualization scripts
notebooks/ Experimental notebooks
data/ Test images and annotations (sample only)
outputs/ Sample visualization results
```


## Environment
- Python 3.8
- PyTorch 2.0.1 + CUDA 11.8
- mmcv 2.0.0
- mmpose 1.x
- mmdet 3.1.0

### env Setting - mmcv
mmcv is installed manually via wheel after env creation.

``` 
pip install --no-cache-dir \
  mmcv==2.0.0 \
  -f https://download.openmmlab.com/mmcv/dist/cu118/torch2.0/index.html
```

## Usage

### 1. Prepare configs
Edit paths in:
- `configs/det_config.py`
- `configs/pose_config.py`

### 2. Run pose inference
```bash
python scripts/run_pose_inference.py \
  --input data/test_images \
  --output outputs
```

### 3. Visualize results
```python
scripts/visualize_keypoints.py \
  --input outputs \
  --save outputs/sample_vis.jpg
```

## Notes
- Large datasets and model weights are not included in this repository.
- Only sample data is provided for testing.
