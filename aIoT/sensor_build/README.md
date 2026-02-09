# sensor_build

본 저장소는 재활 운동 보조 AIoT 시스템 **행가래**의  
센서 및 마이컴 펌웨어 빌드 프로젝트 모음입니다.

각 하위 폴더는 PlatformIO 기반의 독립적인 펌웨어 프로젝트이며,  
사용하는 보드 및 센서 조합에 따라 설정과 동작이 다릅니다.

---

## 디렉터리 구성

```text
sensor_build/
├─ camera_movement/
├─ esp8266_mpu6050/
└─ uno_r4_wifi_hx711/
```

각 디렉터리의 역할은 다음과 같습니다.

- `camera_movement/`  
  Arduino UNO 기반 카메라 무빙 제어 펌웨어입니다.

- `esp8266_mpu6050/`  
  ESP8266(NodeMCU v2) + MPU6050 조합으로  
  상체 재활 운동 시 속도를 가속도 기반으로 측정합니다.

- `uno_r4_wifi_hx711/`  
  Arduino UNO R4 WiFi + HX711 로드셀 조합으로  
  하체 재활 운동 시 힘을 하중 기반으로 측정합니다.

---

## 공통 준비 사항

모든 프로젝트는 다음 환경을 기준으로 빌드합니다.

- PlatformIO 설치  
  VS Code 확장 또는 CLI 방식 모두 사용 가능합니다.

- USB 시리얼 드라이버  
  보드별로 상이하므로 사용 중인 보드에 맞는 드라이버를 설치해야 합니다.

- 각 프로젝트의 `platformio.ini` 확인  
  보드 타입, 업로드 포트, 라이브러리 의존성을 반드시 확인합니다.
  - [`camera_movement/platformio.ini`](./camera_movement/platformio.ini)
  - [`esp8266_mpu6050/platformio.ini`](./esp8266_mpu6050/platformio.ini)
  - [`uno_r4_wifi_hx711/platformio.ini`](./uno_r4_wifi_hx711/platformio.ini)

---

## 공통 빌드 및 업로드 방법

각 펌웨어 프로젝트 디렉터리로 이동한 후  
아래 명령어를 실행합니다.

```bash
# build
pio run

# upload
pio run -t upload

# serial monitor
pio device monitor
```

---

## UDP 통신 구조

모든 센서 노드는 측정된 데이터를 UDP 방식으로 전송하며,  
상위 시스템에서 이를 수신하여 가공합니다.

- 통신 방향  
  센서 → 수신기 단방향 전송

- 전송 주기  
  각 펌웨어 내부 설정값에 따름

- 페이로드 구성  
  센서 측정값(가속도 또는 하중)  
  타임스탬프(옵션)

필요 시 UDP 포트, 패킷 포맷, 엔디안 등의  
프로토콜 정의를 이 문서에 추가할 수 있습니다.

---

## 프로젝트별 메모

### esp8266_mpu6050

- 보드: NodeMCU v2 (ESP8266)
- 통신 속도: 115200
- 의존 라이브러리: I2Cdevlib-MPU6050
- 용도: 상체 재활 운동 속도 감지 (가속도 기반)

---

### camera_movement

- 보드: Arduino UNO
- 통신 속도: 115200
- 용도: 카메라 무빙 제어

---

### uno_r4_wifi_hx711

- 보드: Arduino UNO R4 WiFi
- 통신 속도: 115200
- 의존 라이브러리: HX711
- 업로드 포트(`upload_port`)는 환경에 맞게 수정 필요
- 용도: 하체 재활 운동 힘 감지 (로드셀 기반)

---

## 상세 기능 문서

각 펌웨어의 자세한 동작 방식, 센서 처리 로직, 통신 포맷은  
각 프로젝트 디렉터리의 README 문서를 참고합니다.

- [`camera_movement/README.md`](./camera_movement/README.md)
- [`esp8266_mpu6050/README.md`](./esp8266_mpu6050/README.md)
- [`uno_r4_wifi_hx711/README.md`](./uno_r4_wifi_hx711/README.md)
