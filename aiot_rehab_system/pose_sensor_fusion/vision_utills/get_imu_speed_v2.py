#!/usr/bin/env python3
import socket, json, time, os, math

LISTEN_PORT = 9999

OUT_CSV = "./logs/udp_speed_test.csv"
SAMPLE_HZ = 50.0
DT = 1.0 / SAMPLE_HZ

# 마지막 패킷 이후 이 시간(ms) 넘으면 NaN으로 기록 (원하면 None으로 두면 hold)
STALE_MS = 300.0   # 예: 300ms 이상 새 패킷 없으면 끊김 취급
HOLD_LAST_WHEN_STALE = True  # False면 stale 구간은 NaN

def main():
    os.makedirs(os.path.dirname(OUT_CSV) or ".", exist_ok=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", LISTEN_PORT))
    sock.setblocking(False)

    print(f"[Jetson] listening udp :{LISTEN_PORT}")
    print(f"[Jetson] logging to {OUT_CSV} , sample {SAMPLE_HZ:.1f} Hz")

    f = open(OUT_CSV, "w", buffering=1)
    f.write("t_sec,v,seq,age_ms\n")

    t0 = time.time()
    next_tick = t0

    last_seq = None
    last_v = None
    last_rx_time = None
    last_rx_addr = None

    try:
        while True:
            now = time.time()

            # 1) UDP 수신을 가능한 많이 처리
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                except BlockingIOError:
                    break

                try:
                    msg = json.loads(data.decode("utf-8"))
                    v = float(msg["v"])
                    seq = int(msg.get("seq", -1))

                    # seq jump 출력 (옵션)
                    if seq != -1 and last_seq is not None and seq != last_seq + 1:
                        print(f"[WARN] seq jump {last_seq} -> {seq} from {addr}")
                    if seq != -1:
                        last_seq = seq

                    last_v = v
                    last_rx_time = time.time()
                    last_rx_addr = addr

                except Exception as e:
                    print("bad packet:", data, "err:", e)

            # 2) 고정 간격 tick이 되었으면 CSV에 기록
            if now >= next_tick:
                t_rel = now - t0

                if last_rx_time is None:
                    age_ms = math.inf
                    v_out = float("nan")
                    seq_out = -1
                else:
                    age_ms = (now - last_rx_time) * 1000.0
                    seq_out = last_seq if last_seq is not None else -1

                    if age_ms > STALE_MS and not HOLD_LAST_WHEN_STALE:
                        v_out = float("nan")
                    else:
                        v_out = float(last_v) if last_v is not None else float("nan")

                f.write(f"{t_rel:.6f},{v_out:.6f},{seq_out},{age_ms:.1f}\n")

                # tick 드리프트 방지
                missed = int((now - next_tick) / DT)
                next_tick += (missed + 1) * DT

            # CPU 과점유 방지
            time.sleep(0.001)

    except KeyboardInterrupt:
        pass
    finally:
        try:
            f.flush()
            f.close()
        except Exception:
            pass
        sock.close()
        print("[Jetson] stopped")

if __name__ == "__main__":
    main()
