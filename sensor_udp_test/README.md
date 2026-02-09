# 센서 디바이스 UDP 통신 테스트

상체 운동 속도 / 하체 운동 힘 측정 디바이스가 켜져 있을 때 정상적으로 UDP 통신이 작동하는지 테스트 하는 스크립트 입니다.

- IMU 속도 측정

```bash
python get_imu_strength.py
```
스크립트: [`get_imu_strength.py`](./get_imu_strength.py)

- 로드셀 힘 측정
```bash
python get_load_cell_power.py
```
스크립트: [`get_load_cell_power.py`](./get_load_cell_power.py)
