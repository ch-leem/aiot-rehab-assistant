import socket
import json
import time
import os
import csv
from datetime import datetime

LISTEN_PORT = 9999
LOG_DIR = "./logs"

os.makedirs(LOG_DIR, exist_ok=True)
run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path = os.path.join(LOG_DIR, f"udp_strength_{run_id}.csv")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", LISTEN_PORT))
sock.settimeout(1.0)

print(f"[Jetson] listening udp :{LISTEN_PORT}")
print(f"[Jetson] csv log -> {csv_path}")

last_seq = None
last_time = None

rows = []
header = ["jetson_ts", "dt_ms", "strength", "seq", "board_ts"]

try:
  while True:
    try:
      data, addr = sock.recvfrom(1024)
    except socket.timeout:
      continue

    try:
      msg = json.loads(data.decode("utf-8"))

      strength = float(msg["strength"])
      seq = int(msg.get("seq", -1))
      board_ts = msg.get("ts", None)  # seconds since boot (float)

      now = time.time()
      dt_ms = None if last_time is None else (now - last_time) * 1000.0

      warn = ""
      if seq != -1:
        if last_seq is not None and seq != last_seq + 1:
          warn = f"  [seq jump: {last_seq} -> {seq}]"
        last_seq = seq
      last_time = now

      rows.append([
        now,
        "" if dt_ms is None else f"{dt_ms:.3f}",
        f"{strength:.3f}",
        seq,
        "" if board_ts is None else f"{float(board_ts):.3f}",
      ])

      if dt_ms is None:
        print(f"from {addr} strength={strength:.3f}{warn}")
      else:
        print(f"from {addr} strength={strength:.3f} dt={dt_ms:.1f}ms{warn}")

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
