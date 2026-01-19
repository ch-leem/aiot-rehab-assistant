import socket, json, time

LISTEN_PORT = 9999
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", LISTEN_PORT))

print(f"[Jetson] listening udp :{LISTEN_PORT}")

last_seq = None
last_v = None
last_time = None

while True:
    data, addr = sock.recvfrom(1024)
    try:
        msg = json.loads(data.decode("utf-8"))
        v = float(msg["v"])                 # speed
        seq = int(msg.get("seq", -1))       # optional
        ts = msg.get("ts", None)            # optional

        now = time.time()
        if last_time is not None:
            dt = now - last_time
        else:
            dt = None

        # seq 누락/중복 감지(옵션)
        warn = ""
        if seq != -1:
            if last_seq is not None and seq != last_seq + 1:
                warn = f"  [seq jump: {last_seq} -> {seq}]"
            last_seq = seq

        last_v = v
        last_time = now

        if dt is None:
            print(f"from {addr} v={v:.3f}{warn}")
        else:
            print(f"from {addr} v={v:.3f} dt={dt*1000:.1f}ms{warn}")

    except Exception as e:
        print("bad packet:", data, "err:", e)