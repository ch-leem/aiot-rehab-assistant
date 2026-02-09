# YOLO Pose Distillation Experiment

본 문서는 YOLO11m-pose를 Teacher로,
YOLO11n / YOLO11s-pose를 Student로 설정하여 수행한  
**multi-scale pose distillation 실험 과정과 그 결과를 정리한 문서**이다.

본 실험은 경량 모델의 성능 한계를 탐색하고 
재활 도메인에서 요구되는 keypoint 정밀도를  
지식 증류를 통해 보완할 수 있는지 검증하는 것을 목표로 한다.

단, 본 실험은 **연구적 검증 목적**이며 최종 서비스 적용 대상은 YOLO11m-pose이다.

---

## 1. Distillation Target

- Teacher
  - YOLO11m-pose
  - 21 keypoints
  - 파인튜닝 완료 모델
  - 학습 중 gradient 미전파 (freeze, eval mode)

- Student
  - YOLO11n-pose (초기)
  - 이후 YOLO11s-pose로 확장
  - 21 keypoints
  - 경량 모델 기반 배포 가능성 검증 목적

---

## 2. Distillation Strategy Overview

본 증류 실험은  
**GT 기반 학습 + Teacher 모방 학습을 동시에 수행**하는 구조를 따른다.

### Distillation 구성 요소

| 구분 | 설명 |
| --- | --- |
| Output Distillation | Teacher와 Student의 keypoint 좌표(x, y)를 직접 정렬 |
| Feature Distillation | 중간 layer feature / attention을 정렬 |
| GT Supervision | YOLO 기본 pose loss (GT 기준) 유지 |

#### Total Loss
```
L_total =
L_yolo_pose_GT

λ_kpt * L_kpt_distill

λ_att * L_attention_distill
```

| Loss | 설명 |
| --- | --- |
| L_yolo_pose_GT | YOLO 기본 pose loss |
| L_kpt_distill | Teacher vs Student keypoint 좌표 MSE |
| L_attention_distill | Teacher vs Student feature map MSE |

Loss weight (기본값):

```yaml
loss_weight:
  kpt: 0.3
  attention: 0.2
```

#### 폴더 구조
```
# 폴더 구조
yolon/
├── train/
│   ├── __init__.py
│   ├── distill_trainer.py     # PoseTrainer 상속 (핵심)
│   ├── train.py               # 실행 진입점
│   └── train_baseline_nano.py # nano baseline 비교용 학습
│
├── transfer/
│   ├── export_onnx.py         # PoseTrainer 상속 (핵심)
│   ├── export_test.ipynb      # 변환 후 성능 테스트
│   └── onnx_test.ipynb        # nano baseline 비교용 학습
│
├── distill/
│   ├── __init__.py
│   ├── teacher.py             # teacher load
│   ├── hooks.py               # distill 전략
│   └── losses.py              # distillation loss 전략
│
├── utils/
│   ├── __init__.py
│   ├── config.py              # yaml 로드
│   └── seed.py                # seed 고정
│
├── configs/
│   ├── yolon_kpt.yaml # student
│   ├── distill_kpt.yaml # teacher
│   ├── yolo11n-pose.yaml # nano baseline 학습 및 추론용
│   └── data.yaml  # yolo m 모델 키포인트 추가학습한 자료 (nano baseline 학습 및 추론용)
│
├── model/
│   └── yolon.py # yolon student 로드
│
├── env/
│   └── yolon_distill.yaml # 가상환경 설정
│
├── weights/
│   ├── teacher/yolom_kpt.pt         # YOLO m 21 kp
│   ├── student/yolo11n-base.pt      # YOLO nano 21 kp (baseline)
│   └── export/
│       ├── yolo11n_pose21_clean.pt  # YOLO nano 21 kp (distill)
│       └── yolo11n-pose.onnx        # YOLO nano 21 kp (distill, onnx)
│
└── scripts/
    ├── extract.py # best.pt -> clean.pt 추출
    └── train_distill.sh  # 지식 증류 학습 실행
```

---
#### 역할 분리

| 구성	| 역할 |
| --- | --- |
| PoseTrainer |	dataloader, preprocess, optimizer, save |
| teacher.py |	teacher 로딩 (freeze 포함) |
| hooks.py	| attention 추출 |
| utils.config |	distill 설정 yaml 읽기 |

#### 유틸 용도
| 유틸 | 쓰임 |
| --- | --- |
| utils/config.py |	distill 설정 분리 |
| utils/seed.py	| Trainer 초기화 전에 |
| distill/teacher.py |	Trainer 내부 |
| distill/hooks.py	| Trainer 내부 |
| distill/losses.py	| (선택) 분리 유지 가능 |



## 3. Distillation Experiment Flow

### 3.1 Stage 1 – P5 Layer Distillation

첫 번째 실험에서는  
가장 고수준 feature인 **P5 (stride 32)** 에서만 증류를 적용하였다.

#### 목적

- global context 기반 pose 안정화
- recall 저하 방지

#### 적용 방식

- P5 feature map에서 **attention distillation만 적용**
- keypoint output distillation은 미적용

#### 결과

- pose 붕괴 현상은 일부 완화됨
- 그러나 **mAP50-95 개선 폭은 제한적**

#### 결론

P5 단일 스케일 증류만으로는  
**작은 관절 오차(foot, joint-end)를 줄이기에는 한계**가 있음을 확인하였다.

---

### 3.2 Stage 2 – P3 + P5 Mixed Distillation (Asymmetric)

두 번째 실험에서는  
**P3와 P5를 서로 다른 역할로 분리**하여 증류를 적용하였다.

#### 구조

- **P3 (stride 8)**
  - feature distillation
  - keypoint output distillation

- **P5 (stride 32)**
  - attention distillation only

P3의 비중을 명확히 키워  
**local precision 개선**에 초점을 두었다.

* Loss 초기값
```
distill:
  p3:
    feat: 1.0
    kpt: 1.5
  p5:
    attn: 0.5
```

#### 왜 이 구조가 효과적인가

- mAP50-95는 **작은 keypoint 오차**에 매우 민감
- P3는 가장 높은 spatial resolution을 가짐
- P5는 global context 기반으로 pose 붕괴를 방지

즉,

- P3 → 정밀도
- P5 → 안정성

이라는 역할 분담을 통해  
**high IoU threshold 구간에서 성능 개선**을 기대하였다.

---

### 3.3 Stage 3 – GT 기반 Keypoint Supervision 결합

증류 과정에서  
Teacher 모방만으로는 오히려 **bias가 누적될 수 있음**을 고려하여  
GT 기반 supervision을 결합하였다.

#### 적용 방식

- GT 기반 YOLO pose loss 유지
- Teacher keypoint는 soft target으로만 활용

즉,  
**GT와 Teacher 좌표를 혼합해 학습**하는 구조로 전환하였다.

#### 효과

- Teacher 오류 전파 방지
- Student의 일반화 성능 유지

을 동시에 달성하고자 하였다.

---

### 3.4 Stage 4 – P3 / P4 / P5 Full Multi-scale Distillation

이 단계에서는  
**P3 / P4 / P5 모든 스케일에서 실제 forward output을 사용**하여  
완전한 multi-scale distillation 구조를 구성하였다.

#### 주요 구현 사항

- Student ↔ Teacher 간 **동일 스케일 feature 매칭**
- feature loss 계산 시
  - closure / lambda 제거
  - pickle 안전성 확보
- hook handle 명시적 관리
  - train 종료 시 hook 제거

이로써  
YOLO11n pose student가  
YOLO11m teacher의 **multi-scale feature 표현을 전반적으로 모방**하도록 학습되었다.

이는  
정석적인 **multi-scale pose distillation 구조**에 해당한다.

---

### 3.5 Stage 5 – P3 Attention-only Distillation (30 Epoch)

nano 모델의 구조적 한계를 명확히 파악하기 위해  
**P3 attention-only distillation 실험**을 단독으로 수행하였다.

#### Experimental Setup

- Model: YOLO11n-pose
- Epochs: 30
- Optimizer: MuSGD (auto)
- AMP: ON
- Distillation
  - Teacher: YOLO11m-pose
  - P3 attention feature only
- Effective batch
  - Train: 32
  - Val: 64
- Image size: 640

#### 결과

**Detection (Box)**

- mAP50: 0.987
- mAP50-95: 0.859

**Pose (Keypoints)**

- mAP50: 0.933
- mAP50-95: 0.618

Bounding box 성능은 거의 상한선에 도달했으나,  
keypoint mAP50-95는 **nano 구조적 한계로 인해 충분히 개선되지 않음**을 확인하였다.

---

## 4. Student Model 확장 – YOLO11s

nano 모델에서 관측된  
**keypoint 정밀도 상한(cap)** 문제를 해결하기 위해  
Student 모델을 **YOLO11s-pose**로 확장하였다.

#### Model Scale 비교

- Parameter count
  - nano: 약 3M
  - small: 약 10M

- FLOPs
  - nano: ~8 GFLOPs
  - small: ~24 GFLOPs

#### 목적

- high-resolution joint (발, 발끝) 표현력 확보
- nano 구조적 제약 완화

---

### Multi-scale Feature Distillation 유지

- Teacher: `yolom_kpt.pt`
- Student: YOLO11s-pose

적용 스케일

- P3 (stride 8)
- P4 (stride 16)
- P5 (stride 32)

각 스케일에서

- teacher feature → attention map 생성
- 중요한 spatial location에 더 큰 penalty 부여

---

### Feature Adapter 구조

- 각 scale별 **1×1 Conv adapter** 사용
- Lazy initialization 방식
  - 최초 forward 이후 feature shape 기반 자동 생성

#### 목적

- channel mismatch 방지
- distillation loss 안정화

---

## 5. Summary & Conclusion

### Distillation Experiment – Stage-wise Numeric Results

#### Stage 1 – P5 Layer Distillation

| Metric | Value |
| --- | --- |
| Pose mAP50 | N/A |
| Pose mAP50-95 | 개선 미미 |
| 학습 안정성 | 부분 개선 |
| Pose 붕괴 | 일부 완화 |

---

#### Stage 2 – P3 + P5 Mixed Distillation (Asymmetric)

| Metric | Value |
| --- | --- |
| Pose mAP50 | ↑ |
| Pose mAP50-95 | ↑ (Stage 1 대비) |
| High IoU 구간 성능 | 개선 |
| Local keypoint precision | 개선 |

---

#### Stage 3 – GT + Teacher Keypoint Supervision

| Metric | Value |
| --- | --- |
| 학습 안정성 | ↑ |
| Teacher bias 누적 | 감소 |
| Validation 성능 변동성 | 감소 |
| Pose mAP50-95 | 유지 또는 소폭 ↑ |

---

#### Stage 4 – P3 / P4 / P5 Full Multi-scale Distillation

| Metric | Value |
| --- | --- |
| Pose mAP50 | 안정적 |
| Pose mAP50-95 | 안정적 |
| 학습 수렴 | 가장 안정적 |
| 재현성 | 높음 |

---

#### Stage 5 – P3 Attention-only Distillation (YOLO11n, 30 Epoch)

**Detection (Box)**

| Metric | Value |
| --- | --- |
| mAP50 | 0.987 |
| mAP50-95 | 0.859 |

**Pose (Keypoints)**

| Metric | Value |
| --- | --- |
| mAP50 | 0.933 |
| mAP50-95 | 0.618 |

---

### Student Model Scale Extension – YOLO11s

| Model | Params | FLOPs |
| --- | --- | --- |
| YOLO11n | ~3M | ~8 GFLOPs |
| YOLO11s | ~10M | ~24 GFLOPs |

---

## Final Conclusion
본 증류 실험을 통해 다음을 확인하였다.

- nano 모델은 구조적 한계로 인해  
  **keypoint 정밀도(mAP50-95)에 상한이 존재**
- multi-scale distillation은 이론적으로 타당하나,  
  **일정 수준 이상의 backbone capacity가 필요**
- small 모델은 표현력 측면에서 유의미한 개선을 보였으나,  
  모델 크기 증가로 인해 **Jetson 환경 적용에 제약 발생**

이에 따라 본 프로젝트에서는  
**YOLO11m-pose를 TensorRT로 변환하여 사용하는 전략을 최종 선택**하였으며,

본 증류 실험은  
경량화 가능성을 검증하기 위한 **연구적 시도로서의 의미**를 가진다.



