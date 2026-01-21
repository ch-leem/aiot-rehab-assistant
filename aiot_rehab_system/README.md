pose_sensor_fusion

실행 환경 설정
```bash
# default.yaml 참고해서 run.yaml 생성
# aiot_rehab_system/configs/pose_sensor_fusion/run.yaml
```


재활 운동 직접 실행 방법

```bash
# pwd : aiot_rehab_system/

python -m pose_sensor_fusion.app.rehab_start

```

웹 소켓 기반 실행 및 안전 종료 기능 제공
```bash
# pwd : aiot_rehab_system/

python -m pose_sensor_fusion.app.heartbeat

```
