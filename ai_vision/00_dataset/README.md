# Dataset Pseudo Labeling 및 Annotation 생성

본 문서는 **YOLO11-pose 모델 학습을 위한 데이터셋 생성 과정**과  
**MMPose 기반 pseudo labeling을 활용한 keypoint annotation 전략 및 scripts 파일**을 정리한 문서이다.

본 단계의 목적은 다음과 같다.

- 재활 동작 분석에 적합한 전신 keypoint 데이터 확보  
- 관절 끝(발 포함) keypoint 정밀도 확보  
- YOLO11 pose 학습에 바로 활용 가능한 annotation 생성  

---

### Not included in git
- raw datasets (COCO, HICO)
- processed annotations
- extracted images


### Workflow
1. Run filtering scripts in `scripts/`
2. Generate image list txt files
3. Extract images into `input_images/`


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
- 다운로드 받은 파일 그대로 사용


## 1. Dataset 구성 개요

### 1.1 데이터 출처

- COCO WholeBody 데이터셋 + HICO dataset
- 전신이 명확히 인식되는 사람 이미지를 대상으로 선별  
  
#### Dataset
본 연구에서는 공개 데이터셋을 기반으로 학습 데이터를 구성하였다.

- [COCO Dataset](https://cocodataset.org/#download)  
  - 사람 keypoint annotation을 포함한 대규모 객체 인식 데이터셋
  - WholeBody annotation을 활용하여 전신 pose 인식 기준 확보

- [HICO Dataset](https://umich-ywchao-hico.github.io/)  
  - 사람 행동 및 자세 다양성이 풍부한 데이터셋
  - 재활 동작과 유사한 전신 자세 보강 목적

---

### 1.2 Keypoint 정의

본 프로젝트에서는 기존 **COCO 17 keypoint**에 발 움직임 분석을 위한 keypoint를 추가하여  
**총 21개 keypoint**를 정의하였다.

#### 구성

- 기존 COCO 17 keypoint  
  - nose, eyes, ears  
  - shoulders, elbows, wrists  
  - hips, knees, ankles  

- 추가 keypoint 4개  
  - 좌 / 우 toe  
  - 좌 / 우 heel (뒤꿈치)  

이를 통해 재활 도메인에서 중요한 **하체 균형, 발 지지, 체중 이동 정보**를 보다 정밀하게 반영하고자 하였다.


## 2. Image Selection

학습 데이터 품질을 확보하기 위해  
다음 기준을 만족하는 이미지만을 사용하였다.

- 사람 전신이 프레임 내에 포함된 이미지
- 상체와 하체 관절이 모두 식별 가능한 경우
- 심한 가림(occlusion)이나 극단적인 해상도 저하가 없는 이미지

위 기준을 통해  
**약 21,000장의 전신 인식 이미지**를 최종 학습 데이터로 구성하였다.

---

## 3. Keypoint Definition

본 프로젝트에서는  
기존 COCO keypoint 정의를 확장하여  
총 **21개 keypoint**를 사용하였다.

### 구성

- 기존 COCO 17 keypoints
  - 얼굴, 상체, 하체 주요 관절
- 추가 keypoints (4)
  - 좌 / 우 toe
  - 좌 / 우 heel

이를 통해  
재활 도메인에서 중요한 **발 지지, 체중 이동, 균형 변화**를  
보다 정밀하게 학습할 수 있도록 하였다.

---

## 4. Annotation Generation

선별된 이미지에 대해  
keypoint annotation을 생성하고,  
YOLO pose 모델 학습에 적합한 형태로 변환하였다.

- keypoint 좌표 및 bounding box 생성
- 관절 누락 및 품질이 낮은 annotation 필터링
- YOLO11 pose 학습용 annotation 포맷으로 변환

해당 과정은  
학습에 바로 사용할 수 있는 **정제된 학습 데이터셋 확보**를 목적으로 수행되었다.

(라벨링 및 변환 방식의 상세 구현은 별도 문서에서 다룬다.)

---

## 5. Dataset Split & Usage

- Train / Validation split 고정
- 모든 실험에서 동일한 데이터셋 분할 사용

이를 통해  
모델 구조 및 학습 전략에 따른 성능 차이를  
**데이터 편차 없이 비교**할 수 있도록 하였다.

본 데이터셋은 다음 단계에서 사용되었다.

- YOLO11m-pose fine-tuning
- YOLO11n / YOLO11s pose distillation experiment

---

## 6. Notes & Limitations

- 본 데이터셋은 pseudo labeling 기반으로 생성됨
- 절대적인 GT가 아닌 **학습을 위한 근사 데이터셋**
- 최종 성능 평가는 validation 결과를 기준으로 판단

데이터 품질 한계를 인지한 상태에서,  
모델 구조 및 학습 전략의 효과를 검증하는 용도로 활용하였다.