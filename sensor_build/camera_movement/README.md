## 개요
카메라 무빙용 스텝모터(28BYJ-48 + ULN2003) 제어 펌웨어입니다.
Jetson 등 상위 장치가 시리얼 텍스트 명령으로 목표 위치를 지시하면, 가속/저크 제한을 적용해 부드럽게 이동합니다.
부팅 시 홈 스위치로 자동 호밍합니다.

## 하드웨어
- 보드: Arduino UNO
- 스텝모터: 28BYJ-48 + ULN2003 (Full-step, 2-phase ON)
- 홈 스위치: 디지털 입력(풀업)

### 배선
- IN1 -> D8
- IN2 -> D9
- IN3 -> D10
- IN4 -> D11
- HOME SW -> D2 (`INPUT_PULLUP`, 눌림=LOW)

## 기능 요약
- 스텝 위치 제어 (절대 위치)
- 이동 중 리타겟(MOVE 재전송) 지원
- 속도/가속/저크 제한
- 소프트 리밋(최소/최대 스텝)
- EEPROM에 리밋 저장/로드
- 자동 홈(부팅 시)

## 시리얼 명령
115200bps, 텍스트 명령, 줄바꿈(\n) 종료

- `HOME` : 호밍 재시작
- `MOVE <abs_steps> <time_ms>` : 절대 위치 이동
- `STOP` : 즉시 정지
- `POS?` : 현재 위치 조회
- `LIMIT <min_steps> <max_steps>` : 소프트 리밋 설정
- `SAVE` : 리밋 EEPROM 저장
- `LOAD` : 리밋 EEPROM 로드
- `HELP` : 명령 도움말 출력

## 주요 파라미터(튜닝)
- `MAX_SPEED_SPS`, `MIN_SPEED_SPS`
- `MAX_ACCEL_SPS2`, `MAX_JERK_SPS3`
- `STEP_MIN_POS`, `STEP_MAX_POS`
- `HOME_SPEED_SPS`, `HOME_DEBOUNCE_MS`

## 빌드/업로드
```bash
# pwd : camera_movement/

# build
pio run

# upload
pio run -t upload

# serial monitor
pio device monitor
```

코드 위치: [`src/main.cpp`](./src/main.cpp)
