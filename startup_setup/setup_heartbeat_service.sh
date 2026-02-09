#!/usr/bin/env bash
set -e

SERVICE_NAME=heartbeat.service
SERVICE_PATH=/etc/systemd/system/${SERVICE_NAME}

PROJECT_ROOT=/home/a203/workspace/S14P11A203/aiot_rehab_system
USER_NAME=a203
PYTHON_BIN=/usr/bin/python3
MODULE_NAME=pose_sensor_fusion.app.heartbeat

echo "[1/4] Create systemd service file"

sudo tee ${SERVICE_PATH} > /dev/null <<EOF
[Unit]
Description=AIoT Rehab Heartbeat (WebSocket)
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${PROJECT_ROOT}
ExecStart=${PYTHON_BIN} -m ${MODULE_NAME}

# 개발 단계: 자동 재시작 비활성화
Restart=no

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "[2/4] Reload systemd daemon"
sudo systemctl daemon-reload

echo "[3/4] Enable service (start on boot)"
sudo systemctl enable ${SERVICE_NAME}

echo "[4/4] Done"
echo
echo "Service installed but NOT started."
echo "Start manually with:"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo
echo "Check logs with:"
echo "  journalctl -u ${SERVICE_NAME} -f"
