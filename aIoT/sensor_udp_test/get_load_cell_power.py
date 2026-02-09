import socket
import json
import time
import os
import csv
from datetime import datetime

LISTEN_PORT = 9998
LOG_DIR = "./logs"

os.makedirs(LOG_DIR, exist_ok=True)
run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path = os.path.join(LOG_DIR, f"udp_weight_{run_id}.csv")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", LISTEN_PORT))
sock.settimeout(1.0)

print(f"[Jetson] listening udp :{LISTEN_PORT}")
print(f"[Jetson] csv log -> {csv_path}")

last_seq = None
last_time = None

rows = []
header = ["jetson_ts", "dt_ms", "weight_kg", "seq", "board_ts_ms_or_raw", "raw_json"]

def _get_weight(msg):
    w = msg.get("weight_kg", None)
    if w is None:
        w = msg.get("kg", None)
    if w is None:
        w = msg.get("weight", None)
    return w

try:
    while True:
        try:
            data, addr = sock.recvfrom(2048)
        except socket.timeout:
            continue

        now = time.time()
        dt_ms = None if last_time is None else (now - last_time) * 1000.0

        try:
            s = data.decode("utf-8", errors="replace")
            msg = json.loads(s)

            w_raw = _get_weight(msg)
            weight_kg = float(w_raw) if w_raw is not None else float("nan")

            seq = int(msg.get("seq", -1))

            # ts는 보드 구현에 따라 ms일 수도 있고 seconds일 수도 있어서 일단 raw 그대로 기록
            board_ts = msg.get("ts", None)

            warn = ""
            if seq != -1:
                if last_seq is not None and seq != last_seq + 1:
                    warn = f"  [seq jump: {last_seq} -> {seq}]"
                last_seq = seq

            last_time = now

            rows.append([
                f"{now:.6f}",
                "" if dt_ms is None else f"{dt_ms:.3f}",
                f"{weight_kg:.5f}" if weight_kg == weight_kg else "nan",
                seq,
                "" if board_ts is None else str(board_ts),
                s,
            ])

            if dt_ms is None:
                print(f"from {addr} weight={weight_kg:.5f}kg seq={seq} ts={board_ts}{warn}")
            else:
                print(f"from {addr} weight={weight_kg:.5f}kg dt={dt_ms:.1f}ms seq={seq} ts={board_ts}{warn}")

        except Exception as e:
            print("bad packet:", data, "err:", e)

except KeyboardInterrupt:
    print("\n[Jetson] Ctrl+C received, saving csv...")

finally:
    try:
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        print(f"[Jetson] saved {len(rows)} rows -> {csv_path}")
    except Exception as e:
        print("[Jetson] failed to save csv:", e)

    sock.close()
    print("[Jetson] socket closed")
