## 개요
ESP8266(NodeMCU v2) + MPU6050 기반 상체 운동 속도/강도 감지 펌웨어입니다.
자이로/가속도 데이터를 100Hz로 읽고, 컴플리멘터리 필터로 자세를 추정한 뒤 선형가속도를 기반으로 운동 강도(`strength`)를 계산합니다.
계산 결과는 UDP로 50Hz 전송됩니다.

## 기능 요약
- 센서 샘플링: 100Hz
- 자세 추정: 컴플리멘터리 필터(roll/pitch)
- 중력 제거 후 선형가속도 계산
- 정지 감지(ZUPT) 및 속도 추정(내부 계산, 현재 전송은 `strength`만)
- UDP JSON 송신(50Hz)

## 하드웨어
- 보드: NodeMCU v2 (ESP8266)
- 센서: MPU6050
- I2C 연결:
  - SDA: D2 (GPIO4)
  - SCL: D1 (GPIO5)

## 설정 파일
`include/secrets_exam.h`를 복사해 `include/secrets.h`로 만들고 값 채우기:
- `WIFI_SSID`, `WIFI_PASS`
- 고정 IP 사용 시 `WIFI_USE_STATIC` 및 IP/DNS
- UDP 수신지: `UDP_TARGET_IP`, `UDP_TARGET_PORT`

## UDP 페이로드
JSON 1줄 전송(문자열):
```json
{"strength":12.345,"seq":10,"ts":12.345}
```
- `strength`: 각속도 크기(deg/s)
- `seq`: 증가하는 시퀀스 번호
- `ts`: 부팅 이후 경과 시간(초)

## 빌드/업로드
```bash
# pwd : esp8266_mpu6050/

# build
pio run

# upload
pio run -t upload

# serial monitor
pio device monitor
```

## 참고 파라미터
- `sampleHz`: 100Hz 샘플링
- `plotHz`: 50Hz 전송
- `alpha`: 컴플리멘터리 필터 계수
- `stillLinAccMs2`, `stillGyroDps`, `stillHoldMs`: 정지 감지 튜닝
