# pose_sensor_fusion 상세 기술 문서

카메라(RealSense) 기반 2D/3D 자세 추정 결과와 IMU/로드셀 UDP 센서를 프레임 기준으로 정렬/융합하여
외부로 전송(REST ingest, WebRTC)하거나 로컬에 NDJSON으로 기록하는 모듈입니다.

---

## 모듈 구성

- `app/rehab_start.py`
  - 메인 실행 루프
  - 카메라 프레임 수집 → 포즈 추론 → 센서 매칭 → 페이로드 생성 → 전송

- `app/run_logger.py`
  - 메인 루프와 동일한 파이프라인을 수행
  - 결과를 NDJSON으로 저장 (디버깅/분석 목적)

- `app/heartbeat.py`
  - WebSocket 서버와 연결 유지
  - `run` / `stop` 명령으로 `rehab_start` 프로세스 제어

- `imu/imu_udp_buffer.py`
  - IMU UDP 수신 버퍼
  - host timestamp 기준 nearest/interp 매칭

- `load_cell/load_cell_udp_buffer.py`
  - Load cell UDP 수신 버퍼
  - host timestamp 기준 nearest/interp 매칭

- `utils/`
  - `config_loader.py`: YAML 로딩
  - `create_payload.py`: 템플릿 기반 페이로드 생성
  - `json_logger.py`: NDJSON 로거
  - `ingest_sender.py`: REST ingest 비동기 전송
  - `webrtc_streamer.py`: WebRTC 스트리밍

- `vision_utills/`
  - RealSense 프레임 수집
  - TensorRT 기반 추론
  - 2D/3D 포즈 처리 및 시각화

---

## 실행 방식

### 메인 실행
```bash
# pwd : aiot_rehab_system/
python -m pose_sensor_fusion.app.rehab_start
```

### 로깅 모드 (NDJSON 저장)
```bash
# pwd : aiot_rehab_system/
python -m pose_sensor_fusion.app.run_logger
```

### Heartbeat 실행 (외부 제어)
```bash
# pwd : aiot_rehab_system/
python -m pose_sensor_fusion.app.heartbeat
```

---

## 데이터 처리 흐름

1. 카메라 프레임 수집 (RealSense RGB + Depth)
2. TensorRT 추론으로 2D keypoint 추출
3. Depth 기반 3D 좌표 복원
4. OneEuro Filter로 3D 좌표 smoothing
5. 관절 각도/기울기/속도/힘 계산
6. IMU/로드셀 UDP 버퍼에서 프레임 타임 기준 매칭
7. 페이로드 생성 후 ingest/WebRTC/NDJSON로 출력

---

## UDP 입력

### IMU 입력 포맷
```json
{"strength":12.345,"seq":10,"ts":123456}
```
- `strength`: 각속도 기반 강도 값
- `seq`: 시퀀스 번호
- `ts`: 보드 타임스탬프(ms)

### Load cell 입력 포맷
```json
{"weight_kg":12.345,"ts":123456,"seq":10}
```
- `weight_kg`: 무게(kg)
- `ts`: 보드 타임스탬프(ms)
- `seq`: 시퀀스 번호

---

## 페이로드 구조

페이로드 템플릿은 `configs/data_format_exam/data_payload.json`에 정의되어 있으며,
`utils/create_payload.py`가 템플릿을 복사하여 관절 좌표/각도/센서 값을 삽입합니다.

주요 필드:
- `ts.video_ms`, `ts.host_ms`
- `position.left/right/mid` (3D 좌표 + conf)
- `deg.left/right/mid` (관절 각도/기울기)
- `sensor.strength`, `sensor.power`

---

## 설정 연계

실행 시 `configs/pose_sensor_fusion/run.yaml`을 사용하며,
기본 템플릿은 `configs/pose_sensor_fusion/default.yaml`에 있습니다.

주요 설정:
- `engine.path`: TensorRT 엔진 경로
- `imu.udp_port`, `load_cell.udp_port`
- `webrtc.enable`, `ingest.enable`
- `heartbeat.url`

---

## 동기화/재생

NDJSON 저장 파일은 `sync/post_visualize_json.py`로 재생할 수 있습니다.

```bash
python -m pose_sensor_fusion.sync.post_visualize_json --input <path_to_ndjson>
```

재생 파라미터 예시는 `configs/pose_sensor_fusion/visualize_replay.yaml` 참고.
