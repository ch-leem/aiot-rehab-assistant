#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="jetson-hotspot.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
SCRIPT_PATH="/usr/local/sbin/bringup-hotspot.sh"
HOTSPOT_CONN_NAME="${HOTSPOT_CONN_NAME:-Hotspot}"   # env로 바꿀 수 있음
WAIT_SEC="${WAIT_SEC:-60}"

echo "[1/6] Preflight: require root"
if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root: sudo $0"
  exit 1
fi

echo "[2/6] Create hotspot bring-up script: ${SCRIPT_PATH}"
cat > "${SCRIPT_PATH}" <<EOF
#!/usr/bin/env bash
set -euo pipefail

HOTSPOT_CONN_NAME="${HOTSPOT_CONN_NAME}"
WAIT_SEC="${WAIT_SEC}"

# Wi-Fi 라디오/차단 해제 (혹시 몰라서)
nmcli radio wifi on || true
rfkill unblock wifi || true

# wifi 디바이스가 usable 상태가 될 때까지 대기 (최대 WAIT_SEC)
for i in \$(seq 1 "\${WAIT_SEC}"); do
  dev="\$(nmcli -t -f DEVICE,TYPE dev | awk -F: '\$2=="wifi"{print \$1; exit}')"
  if [[ -n "\${dev}" ]]; then
    state="\$(nmcli -t -f DEVICE,STATE dev | awk -F: -v d="\${dev}" '\$1==d{print \$2}')"

    # unavailable이면 좀 더 기다림
    if [[ -n "\${state}" && "\${state}" != "unavailable" ]]; then
      # 이미 Hotspot이 떠 있으면 성공 처리
      if nmcli -t -f NAME,TYPE,DEVICE connection show --active | grep -q "^\${HOTSPOT_CONN_NAME}:802-11-wireless:"; then
        exit 0
      fi

      # Hotspot 올리기 시도
      if nmcli connection up "\${HOTSPOT_CONN_NAME}"; then
        exit 0
      fi
    fi
  fi
  sleep 1
done

echo "[hotspot] failed: wifi device not ready (timeout=\${WAIT_SEC}s)" >&2
exit 1
EOF

chmod +x "${SCRIPT_PATH}"

echo "[3/6] Create systemd service: ${SERVICE_PATH}"
cat > "${SERVICE_PATH}" <<EOF
[Unit]
Description=Enable WiFi Hotspot on Boot
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=${SCRIPT_PATH}
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

echo "[4/6] Reload systemd"
systemctl daemon-reload

echo "[5/6] Enable + restart service"
systemctl enable "${SERVICE_NAME}"
systemctl reset-failed "${SERVICE_NAME}" || true
systemctl restart "${SERVICE_NAME}"

echo "[6/6] Status"
systemctl status "${SERVICE_NAME}" --no-pager || true

echo
echo "Done."
echo "- Logs: journalctl -u ${SERVICE_NAME} -b --no-pager"
echo "- Active connections: nmcli -t -f NAME,TYPE,DEVICE connection show --active"
echo
echo "Optional: disable autoconnect for a Wi-Fi profile (STA) that blocks hotspot:"
echo "  sudo nmcli connection modify \"<WIFI_PROFILE_NAME>\" connection.autoconnect no"
