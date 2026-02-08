# model_performance_test 상세 기술 문서

YOLO 기반 2D 자세 추정 모델의 성능을 정량 평가하기 위한 스크립트 모음입니다.
TensorRT 엔진을 사용해 추론하고, GT 라벨과 비교하여 OKS 기반 AP를 계산합니다.

---

## 구성

- `test.py`
  - YOLO pose 모델 성능 평가 스크립트
  - 이미지/라벨을 불러와 추론 → OKS/AP 계산

- `yolo_data.yaml`
  - 데이터셋 경로, 클래스, 키포인트 설정

---

## 평가 방식 요약

- 입력 데이터: YOLO Pose 형식 라벨(txt)
- 추론: `TrtEngine`을 통해 TensorRT 엔진 실행
- 매칭: OKS( Object Keypoint Similarity ) 기준
- 지표: AP(평균 정밀도), Precision, Recall

핵심 로직:
- `decode_pose`: 모델 출력 후처리
- `_oks`, `_match_image`, `_compute_ap`: OKS/AP 계산

---

## 실행

```bash
# pwd : aiot_rehab_system/
python -m model_performance_test.test --data <path_to_yolo_data_yaml> --engine <path_to_trt_engine>
```

(옵션/인자 추가가 필요한 경우 `test.py` 상단 argparse를 확인)

---

## 참고

- `pose_sensor_fusion/vision_utills/*`와 동일한 추론/전처리 모듈을 공유합니다.
- 평가용 GT 라벨은 YOLO Pose 형식이어야 합니다.
