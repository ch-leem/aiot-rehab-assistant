## 개요
Arduino UNO R4 WiFi + HX711 기반 하체 운동 힘(로드셀) 측정 펌웨어입니다.
10Hz로 측정하고 median + EMA 필터를 적용한 뒤 UDP로 전송합니다.
제로 트래킹(무게 0 근처 자동 보정)과 시리얼 기반 Tare/Calibrate를 제공합니다.

## 기능 요약
- 샘플링: 10Hz
- 필터: Median(5) + EMA(알파 0.30)
- Zero tracking: 0 근처 자동 오프셋 적응
- UDP JSON 송신(10Hz)
- 시리얼 명령: Tare/Calibrate

## 하드웨어
- 보드: Arduino UNO R4 WiFi
- 센서: HX711 로드셀 앰프
- 핀: DOUT=3, SCK=2

## 설정 파일
[`include/secrets_exam.h`](./include/secrets_exam.h)를 복사해 `include/secrets.h`로 만들고 값 채우기:
- `WIFI_SSID`, `WIFI_PASS`
- 수신지 IP/PORT: `RECV_IP_*`, `RECV_PORT`

## UDP 페이로드
JSON 1줄 전송(문자열):
```json
{"weight_kg":12.345,"ts":123456,"seq":10}
```
- `weight_kg`: 필터된 무게(kg)
- `ts`: 부팅 이후 경과 시간(ms)
- `seq`: 증가하는 시퀀스 번호

## 시리얼 명령
115200bps
- `t` 또는 `T`: Tare (무게 제거 후 오프셋 계산)
- `c` 또는 `C`: Calibrate (알려진 무게 g 입력)

## 캘리브레이션 흐름
1. `c` 입력 후, 알려진 무게(g)를 시리얼에 입력
2. 내부 `cal_factor(counts/g)` 계산 및 EEPROM 저장
3. 이후 재부팅 시 자동 로드

## 빌드/업로드
```bash
# pwd : uno_r4_wifi_hx711/

# build
pio run

# upload
pio run -t upload

# serial monitor
pio device monitor
```

코드 위치: [`src/main.cpp`](./src/main.cpp)
