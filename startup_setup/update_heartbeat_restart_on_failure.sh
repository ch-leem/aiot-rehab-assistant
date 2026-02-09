#!/usr/bin/env bash
set -e

SERVICE_NAME=heartbeat.service
SERVICE_PATH=/etc/systemd/system/${SERVICE_NAME}

echo "[1/4] Check service file exists"
if [ ! -f "${SERVICE_PATH}" ]; then
  echo "ERROR: ${SERVICE_PATH} not found"
  exit 1
fi

echo "[2/4] Update Restart policy -> on-failure"
sudo sed -i \
  -e 's/^Restart=.*/Restart=on-failure/' \
  -e '/^Restart=/! s/\(\[Service\]\)/\1\nRestart=on-failure/' \
  "${SERVICE_PATH}"

echo "[3/4] Reload systemd daemon"
sudo systemctl daemon-reload

echo "[4/4] Restart service to apply policy"
sudo systemctl restart ${SERVICE_NAME}

echo
echo "Restart policy updated:"
echo "  Restart=on-failure"
echo
echo "Verify with:"
echo "  systemctl cat ${SERVICE_NAME}"
