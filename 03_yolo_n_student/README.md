# YOLO Distillation Experiment

## Target
- Student: YOLO-n (nano), 21 keypoints
- Teacher: YOLO-m (from 03_YOLO M)

## 증류 규칙

이번 작업은 Output-level + Feature-level distillation의 결합이다.
| 구분 | 설명 |
| :---: | :---: |
| Output Distillation | Teacher와 Student의 keypoint 좌표(x, y)를 직접 맞추도록 학습 |
| Feature Distillation | 중간 layer의 attention(feature map)을 맞추도록 학습 |
| GT Supervision | 기존 YOLO pose loss (GT keypoint, box 등)도 유지 |



1) Keypoint Output Distillation

- Teacher와 Student의 **관절 좌표(x, y)**를 직접 정렬
- 좌표 단위의 MSE Loss 적용

2) Feature / Attention Distillation

- 동일한 중간 layer에서 feature map 추출
- Teacher / Student의 attention map을 MSE로 정렬
- 관절을 바라보는 “시선” 자체를 학습시키는 효과


| GT 기반 학습 + Teacher 모방 학습을 동시에 수행


## Teacher / Student 구성
- Teacher 모델

YOLO11-m pose

21 keypoints

파인튜닝된 고정 모델

학습 중 gradient 미전파 (eval mode)

- Student 모델

YOLO11-n pose

동일한 21 keypoints

최종 배포 대상


## Loss 구성
최종 Loss 함수
```
L_total =
    L_yolo_pose_GT
  + λ_kpt * L_kpt_distill
  + λ_att * L_attention_distill
```
| Loss | 설명 |
| --- | --- |
| L_yolo_pose_GT | YOLO 기본 pose loss (GT 기준) |
| L_kpt_distill | Teacher vs Student keypoint 좌표 MSE |
| L_attention_distill | Teacher vs Student feature map MSE|


```
loss_weight:
kpt: 0.3
attention: 0.2
```
로 사용


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
### 역할 분리

| 구성	| 역할 |
| --- | --- |
| PoseTrainer |	dataloader, preprocess, optimizer, save |
| teacher.py |	teacher 로딩 (freeze 포함) |
| hooks.py	| attention 추출 |
| utils.config |	distill 설정 yaml 읽기 |

### 유틸 용도
| 유틸 | 쓰임 |
| --- | --- |
| utils/config.py |	distill 설정 분리 |
| utils/seed.py	| Trainer 초기화 전에 |
| distill/teacher.py |	Trainer 내부 |
| distill/hooks.py	| Trainer 내부 |
distill/losses.py	| (선택) 분리 유지 가능 |