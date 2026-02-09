# AI (Vision) – YOLO11 Pose 연구 및 실행 가이드

본 문서는 본 프로젝트에서 수행한 **YOLO11m-pose 파인튜닝 중심의 연구 과정**과 **YOLO11n 지식증류 실험**, 그리고 **Jetson Orin Nano 배포 환경**까지의 전체 흐름을 정리한 문서이다.

본 AI 파트의 목표는 다음과 같다.

- 재활 도메인에 적합한 pose estimation 성능 확보
- YOLO11m-pose 파인튜닝을 통한 정확도 향상
- YOLO11n-pose 증류를 통한 경량화 및 엣지 디바이스(Jetson) 배포 가능성 검증
- 연구 재현성과 실험 추적 가능성 확보

담당자

- AI 모델 연구 및 구현: 정예진

---

## 목차

1. 프로젝트 개요  
2. 개발 환경  
3. 기술 스택  
4. 모델 선정 이유  
5. 전체 Pipeline  
6. 연구 흐름 및 주요 고민  
7. 연구 과정 상세  
   - 7.1 Dataset pseudo labeling  
   - 7.2 YOLO11m-pose fine-tuning  
   - 7.3 YOLO11n-pose distillation experiment  
8. 에러 발생 시 대응 방안 및 제한 사항  
9. 오픈소스 라이브러리  
10. 담당자  

---

## 1. 개발 환경

### 학습 서버 환경

- OS
  - Jupyter Notebook 기반 환경
  - Linux console 사용
- GPU
  - NVIDIA Tesla V100-PCIE-32GB
- Python / 가상환경
  - Conda 기반 가상환경 사용
  - 연구 단계별로 환경 분리하여 관리

### 단계별 가상환경 구성

본 프로젝트에서는 연구 단계별 의존성 충돌을 방지하기 위해  
아래와 같이 **yaml 단위로 가상환경을 분리**하였다.

- Dataset pseudo labeling
  - mmpose_env.yaml
  - MMPose 기반 pseudo labeling 및 skeleton 처리
- YOLO11m-pose fine-tuning
  - yolom_train_env.yaml
  - Ultralytics YOLO11m-pose 학습 전용 환경
- YOLO11n-pose distillation
  - yolon_distill.yaml
  - 증류 로직(hook, loss) 커스터마이징 환경

각 yaml 파일은 연구 단계 README에서 상세히 설명한다.

---

## 2. 기술 스택

- 모델 / 학습
  - Ultralytics YOLO11-pose (m, n)
  - PyTorch
- 데이터 처리
  - COCO 기반 keypoint 데이터
  - HICO 데이터셋
  - MMPose 기반 pseudo labeling
  - YOLO pose annotation 변환 스크립트
- 실험 및 분석
  - TensorBoard
  - 커스텀 로그(csv, print 기반 실험 기록)
- 배포 / 추론
  - ONNX
  - TensorRT
  - Jetson Orin Nano

---

## 3. 실행 환경 (Jetson Orin Nano + TensorRT)

### 타깃 디바이스

- Jetson Orin Nano

### 배포 전략

- 학습 서버에서 PyTorch(.pt) 모델 학습
- ONNX 변환 후 TensorRT .engine 파일 생성
- Jetson에서 .engine 기반 추론 수행

### 고려 사항

- TensorRT 엔진은 Jetson 환경에 종속적
- 입력 해상도(imgsz), FP16 여부, dynamic shape 설정에 따라 엔진 재생성 필요
- Jetson 실시간 추론을 고려하여 YOLO11n-pose 증류 실험 수행

Jetson 변환 및 추론 상세는 `inference/README.md`에 정리한다.

---

## 4. 모델 선정 이유

### 4.1 재활 도메인 요구사항

- 상체 및 하체의 관절 각도 변화가 핵심 지표
- 실시간 혹은 준실시간 피드백 제공 필요
- 병원/센터 환경에서 엣지 디바이스 사용 가능성 고려
- keypoint 정밀도가 bbox 정확도보다 중요

### 4.2 후보 모델 비교

- MMPose (HRNet, RTMPose 등)
- YOLO Pose 계열
- OpenPose 계열

### 4.3 YOLO11-pose(m, n) 최종 선택 이유

- 최신 YOLO Pose 구조
- m 모델을 통한 정확도 확보
- n 모델을 통한 증류 실험 가능
- Ultralytics 기반 파이프라인 단순화

---

## 5. 전체 Pipeline

| 단계 | 목적 | 상세 문서 |
| --- | --- | --- |
| Dataset pseudo labeling | 데이터 품질 확보 | dataset/README.md |
| YOLO11m fine-tuning | 정확도 향상 | yolom_finetune/README.md |
| YOLO11n distillation | 경량화 검증 | yolon_distill/README.md |

---

## 6. 연구 흐름 및 주요 고민

### 6.1 초기 가설

- m 모델로 정확도 확보
- n 모델 증류로 Jetson 실시간 추론 가능성 검증

### 6.2 구조적 한계 인식

- nano 모델의 표현력 한계
- mAP50-95에서 성능 저하

### 6.3 지식증류 실험 결과

- YOLO11n: mAP50 개선, mAP50-95 한계
- YOLO11s: 성능 향상, 모델 용량 증가로 Jetson 적용 불가

### 6.4 최종 의사결정

- YOLO11m-pose + TensorRT 선택
- 증류는 연구적 시도로 한정

### 6.5 연구 인사이트

- keypoint 표현력이 최우선
- TensorRT 최적화가 경량화보다 효과적일 수 있음
- 연구와 서비스 적용 판단은 분리 필요

---

## 7. 연구 상세 내용

### 7.1 Dataset pseudo labeling

→ dataset/README.md

### 7.2 YOLO11m-pose Fine-tuning

→ yolom_finetune/README.md

### 7.3 YOLO11n-pose Distillation Experiment

→ yolon_distill/README.md

---

## 8. 에러 발생 시 대응 방안 및 제한 사항

### 데이터

- corrupt 이미지 제거
- low-confidence keypoint 필터링

### 학습

- OOM 시 imgsz / batch 조정
- distillation hook 범위 제한

### 모델 구조

- TensorRT 변환 고려한 구조 유지
- 일부 keypoint 손실 구조적 한계 존재

---

## 9. 오픈소스 라이브러리

- Ultralytics YOLO
- PyTorch
- MMPose
- OpenCV
- ONNX
- TensorRT

각 라이브러리의 라이선스는 원문을 따른다.

### 디렉터리 구조
```
ai/
  README.md
  00_dataset/
    README.md
  01_mmpose_labeling/
    README.md
  02_yolo_m_teacher/
    README.md
  03_yolo_n_stduent/
    README.md
```

