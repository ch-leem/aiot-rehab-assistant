import os

# ===== IMU =====
IMU_UDP_IP = os.getenv("IMU_UDP_IP", "0.0.0.0")
IMU_UDP_PORT = int(os.getenv("IMU_UDP_PORT", "9999"))
IMU_MATCH = os.getenv("IMU_MATCH", "nearest")  # nearest | interp
IMU_BUFFER_SEC = float(os.getenv("IMU_BUFFER_SEC", "8.0"))
IMU_MAX_ABS_AGE_MS = float(os.getenv("IMU_MAX_ABS_AGE_MS", "500.0"))

# ===== Logging =====
LOG_DIR = os.getenv("LOG_DIR", "./logs")
