# Pose + IMU CSV Logger

This project logs (1) depth+pose results and (2) IMU UDP packets into a single CSV, aligned per video frame.

## Files
- `pose_imu_logger/app/run_pose_imu_logger.py` : main runner
- `pose_imu_logger/sync/sync_and_plot.py` : offline alignment + plots
- `pose_imu_logger/vendor/` : your uploaded code copied as-is

## IMU UDP packet format
Send JSON via UDP to `IMU_UDP_PORT` (default 9999):

```json
{"v": 12.34, "seq": 123, "ts": 456789}
```
- `v` : your intensity value (you called it cm/s)
- `seq` : monotonically increasing packet sequence
- `ts` : ESP `millis()` (optional but recommended)

## Run
Example:

```bash
mkdir -p logs
IMU_UDP_PORT=9999 IMU_MATCH=nearest LOG_DIR=./logs \
python3 -m pose_imu_logger.app.run_pose_imu_logger
```

Stop with `q` or `ESC`.

The CSV is created under `LOG_DIR`.

## Offline sync & plot

```bash
python3 -m pose_imu_logger.sync.sync_and_plot ./logs/pose_imu_*.csv --maxlag_ms 800
```
