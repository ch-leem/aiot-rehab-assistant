# [`heartbeat.py`](../aiot_rehab_system/pose_sensor_fusion/app/heartbeat.py) 자동 시작 설정 스크립트


## 실행 방법


프로그램 자동 재시작 없음
```
chmod +x setup_heartbeat_service.sh
./setup_heartbeat_service.sh
```
스크립트: [`setup_heartbeat_service.sh`](./setup_heartbeat_service.sh)


프로그램 에러로 종료 시에만 재시작 (직접 종료하거나, 프로그램 정상 종료시는 재시작 없음)

```
chmod +x update_heartbeat_restart_on_failure.sh
./update_heartbeat_restart_on_failure.sh
```
스크립트: [`update_heartbeat_restart_on_failure.sh`](./update_heartbeat_restart_on_failure.sh)


수동 실행
```
sudo systemctl start heartbeat.service
```

수동 종료
```
sudo systemctl stop heartbeat.service
```


로그 보기
```
journalctl -u heartbeat.service -f
```

부팅 시 자동 시작 끄기
```
sudo systemctl disable heartbeat.service
```
