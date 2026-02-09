
# MMPose Pseudo Labeling Pipeline

본 디렉토리는 **MMPose 모델을 기반으로 한 pseudo labeling 파이프라인**을 구현한 공간이다.  
YOLO11-pose 모델 학습을 위한 **전신 keypoint GT 생성**을 목적으로 사용된다.

---

## Overview

- Person detection: RTMDet (MMDetection)
- Pose estimation: MMPose (Top-down)
- Keypoints: 21 points (COCO 17 + Foot 4)
- Output:
  - COCO-style keypoint annotations
  - YOLO11 pose 학습용 annotation (.txt)

본 파이프라인은  
수동 라벨링 비용을 최소화하면서도  
재활 도메인에 적합한 전신 pose 데이터를 확보하는 것을 목표로 설계되었다.

---

## Directory Structure
```
configs/ Model configuration and checkpoint paths
scripts/ Pose inference, filtering, and annotation conversion scripts
notebooks/ Experimental notebooks (debugging, visualization)
data/ Input images and sample annotations (sample only)
outputs/ Pseudo labeling results and visualizations

```
---

## Environment

- Python 3.8
- PyTorch 2.0.1 + CUDA 11.8
- mmcv 2.0.0
- mmpose 1.x
- mmdet 3.1.0

### Environment Setting – mmcv

`mmcv`는 가상환경 생성 이후  
CUDA 및 PyTorch 버전에 맞는 wheel 파일을 사용하여 수동 설치하였다.

```bash
pip install --no-cache-dir \
  mmcv==2.0.0 \
  -f https://download.openmmlab.com/mmcv/dist/cu118/torch2.0/index.html
```

## Pseudo Labeling Pipeline
### 1. Input Data Preparation

#### 입력 데이터

- 전신이 포함된 사람 이미지

#### 사전 필터링 기준

- 상체와 하체가 모두 프레임 내에 존재하는 경우
- 극단적인 occlusion이 발생하지 않은 경우
- 해상도가 지나치게 낮은 이미지 제외

위 기준을 적용하여  
약 **21,000장의 전신 인식 이미지**를 pseudo labeling 대상으로 최종 선별하였다.

본 단계는 전신 pose 추정이 불가능한 데이터로 인한  
pseudo label 품질 저하를 방지하기 위한 사전 정제 과정이다.

---

### 2. Person Detection

- RTMDet (MMDetection) 사용
- 이미지 내 사람 bounding box 검출
- Top-down pose estimation을 위한 ROI 생성

검출된 bounding box는 이후 pose estimation 단계에서 입력으로 사용된다.

---

### 3. Pose Estimation

- MMPose Top-down 모델 적용
- COCO WholeBody 기반 keypoint 추정

#### 사용 keypoints

- COCO 17 keypoints
- Foot keypoints 4
  - left toe
  - right toe
  - left heel
  - right heel

#### 출력 정보

- keypoint 좌표 (x, y)
- confidence score

해당 출력은 후속 단계에서 keypoint GT 생성의 기반으로 활용된다.

---

### 4. Keypoint Filtering & Quality Control

pseudo label 품질 확보를 위해 다음 기준을 적용하여 keypoint를 정제하였다.

- confidence score threshold 적용
- 프레임 외부로 벗어난 keypoint 제거
- 극단적인 좌표 이상치 제거
- 주요 관절 및 발 keypoint가 누락된 샘플 제외

이를 통해 학습에 악영향을 줄 수 있는 **노이즈 라벨을 최소화**하였다.

---

### 5. Annotation Conversion (YOLO11 Pose)

정제된 keypoint GT를 **YOLO11-pose 학습용 annotation 포맷**으로 변환하였다.

#### 변환 내용

- class id
- bounding box (cx, cy, w, h) – normalized
- keypoints (x, y, visibility) – normalized

#### 출력 형식

- 이미지 파일: `.jpg`
- annotation 파일: `.txt`
- 이미지와 동일한 파일명 사용

변환된 annotation은 YOLO11m-pose 및 YOLO11n-pose 학습에  
별도의 추가 전처리 없이 바로 사용 가능하다.

---

## Usage

### 1. Prepare configs

다음 파일에서 모델 및 checkpoint 경로를 설정한다.

- `configs/det_config.py`
- `configs/pose_config.py`

---

### 2. Run pseudo labeling

```bash
python scripts/run_pose_inference.py \
  --input data/input_images \
  --output outputs
```

### 3. Visualize keypoints
```bash
python scripts/visualize_keypoints.py \
  --input outputs \
  --save outputs/sample_vis.jpg
```

### Notes

대규모 데이터셋 및 pretrained model weight는 저장소에 포함되지 않는다.
본 디렉토리에는 테스트 및 문서화를 위한 sample 데이터만 포함된다.
pseudo labeling 결과는 절대적 GT가 아닌, 학습을 위한 근사치로 활용한다.