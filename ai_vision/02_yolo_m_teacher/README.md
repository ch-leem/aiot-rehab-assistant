# YOLO11m-pose Fine-tuning

본 문서는 재활 도메인에 적합한 pose estimation 성능 확보를 위해 
**YOLO11m-pose 모델을 파인튜닝한 과정과 결과**를 정리한 문서이다.

본 단계는 본 프로젝트에서 **최종 서비스 적용을 목표로 수행한 핵심 모델 학습 단계**에 해당한다.

---

## Training Summary

- Model  
  - YOLO11m-pose

- Keypoints  
  - 21 points  
  - COCO 17 keypoints + Foot keypoints 4 (toe, heel)

- Training configuration  
  - Epochs: 100

- Performance  
  - Pose mAP50: 0.988  
  - Pose mAP50-95: 0.872  

- Inference speed  
  - 약 2.5 ms / image  
  - 환경: NVIDIA Tesla V100-PCIE-32GB

본 결과를 통해  
재활 동작 분석에 요구되는 **keypoint 정밀도와 안정성**을  
충분히 확보할 수 있음을 확인하였다.

---

## Pipeline

YOLO11m-pose 파인튜닝은 다음 파이프라인으로 진행되었다.

1. Dataset split (labels 기준)  
2. Pose training (YOLO11m-pose)  
3. Validation  
4. Image / Video inference를 통한 정성 평가  

정량 지표(mAP)와 함께  
실제 재활 동작 이미지 및 영상 추론 결과를 통해  
keypoint 안정성을 함께 검증하였다.

---

## Dataset 구성 및 분할

### Dataset 구성

- MMPose 기반 pseudo labeling으로 생성된 데이터셋 사용
- 전신이 명확히 인식되는 이미지 약 6,395장
- 21 keypoints 기준 annotation
- dataset 단계에서 생성한 YOLO pose annotation 활용

### Dataset Split 전략

- labels 기준 train / validation split 수행
- 실험 간 데이터 편차를 제거하기 위해 split 기준 고정
- 증류 실험과의 공정 비교를 위해 동일 split 유지

---

## Training Environment

- OS  
  - Linux (Jupyter Notebook 기반 환경)

- GPU  
  - NVIDIA Tesla V100-PCIE-32GB

- Framework  
  - Ultralytics YOLO11-pose  
  - PyTorch

- Virtual Environment  
  - yolom_train_env.yaml  
  - YOLO11m-pose 학습 전용 환경

---

## Model & Configuration

### Base Model

- Pretrained weight  
  - yolo11m-pose.pt (Ultralytics 제공)

### Model Configuration

- `yolo11m_pose.yaml`
- keypoint 개수 21로 확장하여 사용

### Dataset Configuration

- `data.yaml`
- train / val 경로
- keypoint 수 및 annotation 포맷 정의

---

## Directory Structure

본 단계의 작업 디렉터리 구조는 다음과 같다.

```text
workspace/
├── datasets/
│   ├── images/
│   │   ├── train/
│   │   └── val/
│   ├── input_images/
│   │   └── ...
│   └── labels/
│       └── ...
│
├── yolom/
│   ├── dataset/
│   │   └── data.yaml
│   │
│   ├── models/
│   │   ├── yolo11m_pose.yaml
│   │   └── ...
│   │
│   ├── runs/
│   │   └── pose/
│   │       └── yolo11m_pose_21points/
│   │           ├── weights/
│   │           │   ├── best.pt
│   │           │   └── last.pt
│   │           ├── args.yaml
│   │           └── results (images, results.csv)
│   │
│   ├── scripts/
│   │   └── ...
│   │
│   ├── weights/
│   │   └── yolo11m-pose.pt
│   │
│   ├── yolom_train_env.yaml
│   │
│   └── README.md
│
├── mmpose/
│
└── yolon/
```


## Quantitative Results (TensorRT, 21 Keypoints)

### Overall Performance

| Model | mAP50 | mAP50-95 | Inference Time (ms) |
| --- | --- | --- | --- |
| YOLO11 m pose 21 (TensorRT) | 0.990 | 0.920 | 29.46 |

YOLO11m-pose는 TensorRT 변환 이후에도  
높은 정확도와 안정적인 추론 성능을 유지하였다.

특히 mAP50-95 지표에서의 성능은  
재활 도메인에서 중요한 **관절 끝(keypoint)의 정밀한 위치 추정 성능**이  
충분히 확보되었음을 의미한다.

---

### Test Image 기준 성능 (1267 images)

| Model | mAP50 | mAP50-95 | Pose Detections | GPU Inference (ms/image) |
| --- | --- | --- | --- | --- |
| YOLO11 m pose 17 (TensorRT, default) | 0.872 | 0.747 | 2766 | 31.06 |
| YOLO11 m pose 21 (TensorRT, ours) | 0.988 | 0.925 | 1273 | 29.46 |

관절 수를 **17 → 21**로 확장하고  
pseudo labeling 기반으로 재학습한 결과,

- mAP50 및 mAP50-95 모두 크게 향상
- 오히려 추론 속도는 소폭 개선

되는 효과를 확인하였다.

이는 단순한 keypoint 추가가 아니라,  
모델의 **자세 표현 능력과 detection quality가 함께 개선**되었음을 의미한다.

---

### Detection Confidence Distribution Analysis

동일한 NMS 및 confidence threshold 조건에서  
최종 검출된 pose 수가 **약 50% 감소**하였다.

- default (17 keypoints): 2766 detections  
- ours (21 keypoints): 1273 detections  

검출 수 감소는 성능 저하가 아닌,  
**detection confidence 분포가 더 명확해졌음을 의미**한다.

#### Interpretation

- True detection에는 높은 confidence score가 집중
- False detection은 낮은 score 영역으로 이동

즉, 모델이 **올바른 자세에는 더 확신**을 가지고
잘못된 자세에는 낮은 확신을 부여하도록 학습되었음을 의미한다.

이 결과는 mAP 상승과 검출 수 감소가 동시에 발생했다는 점에서
단순 threshold 조정이 아닌 **모델 자체의 분별력 향상**으로 해석할 수 있다.

---

### System-Level Implication

최종 검출 수 감소는 CPU 기반 후처리 연산(NMS, filtering) 감소로 이어진다.

이는 다음과 같은 의미를 가진다.

- 추가적인 모델 경량화 없이도
- 온디바이스 환경에서의 처리 효율 개선 가능성 확인

즉, YOLO11m-pose는  
모델 크기 대비 **정확도, 안정성, 시스템 효율성의 균형이 가장 우수한 선택지**로 판단된다.

---

### Limitations & Considerations

- YOLO11m-pose는 경량 모델 대비 모델 크기가 큼
- 엣지 디바이스 적용 시 TensorRT 변환이 필수
- 실시간성 확보를 위해 배포 전략 최적화 필요

이러한 한계로 인해 후속 단계에서 **경량 모델 기반 증류 실험을 연구적으로 수행**하였으나 
본 프로젝트의 최종 서비스 적용 대상은 YOLO11m-pose로 결정하였다.
