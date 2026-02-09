# YOLOv11 Pose 모델 ONNX 변환 및 TensorRT 엔진 생성

이 저장소는 YOLOv11 Pose 모델(.pt)을 Jetson Orin Nano 환경에서  
실시간 추론이 가능한 TensorRT 엔진으로 변환하기 위한 코드와 예제를 제공합니다.

---

## 실험 환경

### Hardware Environment

- 디바이스: NVIDIA Jetson Orin Nano
- GPU: Ampere 아키텍처, 1024 CUDA 코어
- 메모리: 8GB LPDDR5

### Software Environment

- OS: Ubuntu 22.04
- JetPack: 6.0
- TensorRT: 8.x

---

## 사용 방법

### 1. YOLOv11 Pose 모델 ONNX 변환

다음 명령어를 사용하여 YOLOv11 Pose 모델을 ONNX 형식으로 변환합니다.

```bash
python create_onnx.py \
  --model yolo11n-pose.pt \
  --imgsz 640 \
  --opset 17
```

스크립트: [`create_onnx.py`](./create_onnx.py)

#### Arguments

```text
--model
  변환할 YOLO 모델(.pt) 경로입니다. 필수 인자입니다.

--imgsz
  입력 이미지 해상도입니다. 기본값은 640입니다.

--opset
  ONNX opset 버전입니다. 기본값은 17입니다.

--simplify
  ONNX 그래프 단순화 옵션입니다. 지정 시 활성화됩니다.
```

---

### 2. TensorRT 엔진 생성

다음 명령어를 사용하여 ONNX 모델을 TensorRT FP16 엔진으로 변환합니다.

```bash
/usr/src/tensorrt/bin/trtexec \
  --onnx=yolo11n-pose.onnx \
  --saveEngine=yolo11n-pose_fp16.engine \
  --fp16 \
  --memPoolSize=workspace:2048M \
  --skipInference
```

#### Arguments

```text
--onnx
  TensorRT 엔진으로 변환할 ONNX 모델 경로입니다.

--saveEngine
  생성될 TensorRT 엔진 파일 경로입니다.

--fp16
  FP16 정밀도로 엔진을 생성하여 추론 속도 및 메모리 사용량을 개선합니다.

--memPoolSize=workspace:2048M
  엔진 빌드 시 사용할 workspace 메모리 크기입니다.
  Jetson Orin Nano 환경에서 안정적인 빌드를 위해 2GB로 설정합니다.

--skipInference
  엔진 생성 후 추론을 실행하지 않고 빌드만 수행합니다.
```

---

### 3. 변환된 TensorRT 엔진 비교

[`compare_engine.py`](./compare_engine.py)

이 스크립트는 TensorRT 엔진 교체 시 기존 wrapper 코드를 수정하지 않고  
재사용할 수 있는지 빠르게 판단하기 위한 검증 도구입니다.

```bash
python compare_engine.py \
  --engine_a yolo11m-pose_fp16.engine \
  --engine_b yolo11n-pose_fp16.engine
```

입력, 출력 텐서 구성, shape, dtype, 텐서 순서를 비교하여  
엔진 교체만으로 동작 가능한지 여부를 출력합니다.

---

## 한 줄 요약

본 저장소는 YOLOv11 Pose 모델을 Jetson Orin Nano 환경에서  
ONNX 변환부터 TensorRT FP16 엔진 생성, 엔진 호환성 검증까지  
전체 과정을 정리한 예제입니다.
