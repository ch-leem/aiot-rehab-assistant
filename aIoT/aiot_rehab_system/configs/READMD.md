# configs 상세 기술 문서

`aiot_rehab_system/configs`는 실행 및 데이터 포맷 관련 설정 파일을 관리합니다.
메인 실행은 `pose_sensor_fusion/run.yaml`을 사용하며, 기본 템플릿은 [`default.yaml`](./pose_sensor_fusion/default.yaml)입니다.

---

## 디렉터리 구조

- `pose_sensor_fusion/`
  - [`default.yaml`](./pose_sensor_fusion/default.yaml): 기본 설정 템플릿
  - [`visualize_replay.yaml`](./pose_sensor_fusion/visualize_replay.yaml): NDJSON/CSV 재생 시각화 설정

- `data_format_exam/`
  - [`data_payload.json`](./data_format_exam/data_payload.json): 페이로드 JSON 템플릿
  - [`deg_name_mapping.json`](./data_format_exam/deg_name_mapping.json): 각도 이름 매핑(참고용)

---

## pose_sensor_fusion 설정 요약

[`pose_sensor_fusion/default.yaml`](./pose_sensor_fusion/default.yaml) 주요 항목:

- `engine.path` : TensorRT 엔진 경로
- `inference.*` : YOLO 추론 임계값
- `tracking.*` : 추적 유지 파라미터
- `depth.*` : 깊이 샘플링 및 이상치 제거
- `filter.*` : OneEuro 필터 계수
- `stream.*` : RGB 해상도 및 FPS
- `logging.*` : 로그 출력 디렉터리 및 payload 템플릿 경로
- `imu.*` : IMU UDP 수신 포트/매칭/버퍼
- `load_cell.*` : 로드셀 UDP 수신 포트/매칭/버퍼
- `ingest.*` : REST ingest 설정
- `webrtc.*` : WebRTC 스트리밍 설정
- `heartbeat.*` : WebSocket 서버 설정
- `local_vis.*` : 로컬 시각화 옵션

---

## payload 템플릿

[`data_format_exam/data_payload.json`](./data_format_exam/data_payload.json)은 페이로드 프레임 구조의 스키마 예시입니다.
[`pose_sensor_fusion/utils/create_payload.py`](../pose_sensor_fusion/utils/create_payload.py)에서 이 템플릿을 deep copy하여
각 프레임의 관절 좌표/각도/센서 값을 채웁니다.

---

## visualize_replay 설정

[`pose_sensor_fusion/visualize_replay.yaml`](./pose_sensor_fusion/visualize_replay.yaml)은 NDJSON/CSV 재생 시각화 옵션을 제공합니다.
주요 항목:
- `ndjson.path`: 재생 파일 경로
- `range.start_idx`, `range.end_idx`: 재생 구간
- `replay.*`: FPS, 기록 타임스탬프 사용 여부
- `plot.*`: 그래프 범위 및 색상
