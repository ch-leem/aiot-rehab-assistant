#!/usr/bin/env python3
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def ema(x, alpha=0.15):
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    y = np.empty_like(x, dtype=float)
    y[0] = x[0]
    for i in range(1, x.size):
        y[i] = alpha * x[i] + (1.0 - alpha) * y[i-1]
    return y


def zscore(x):
    x = np.asarray(x, dtype=float)
    s = np.std(x) + 1e-9
    return (x - np.mean(x)) / s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="CSV created by run_pose_imu_logger")
    ap.add_argument("--maxlag_ms", type=float, default=800.0)
    ap.add_argument("--alpha", type=float, default=0.15, help="EMA smoothing")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    host_ms = df["host_ts_ms"].to_numpy(dtype=float)
    t = (host_ms - host_ms[0]) / 1000.0
    if t.size > 2:
        dt = float(np.median(np.diff(t)))
    else:
        dt = 1.0 / 30.0

    imu = np.nan_to_num(df["imu_v_cmps"].to_numpy(dtype=float), nan=0.0)
    rw = np.nan_to_num(df["r_wrist_speed_mps"].to_numpy(dtype=float), nan=0.0)

    imu_s = ema(imu, alpha=args.alpha)
    rw_s = ema(rw, alpha=args.alpha)

    imu_z = zscore(imu_s)
    rw_z = zscore(rw_s)

    maxlag = int((args.maxlag_ms / 1000.0) / max(dt, 1e-6))
    lags = np.arange(-maxlag, maxlag + 1)

    corr = []
    for k in lags:
        if k < 0:
            c = float(np.dot(imu_z[:k], rw_z[-k:]))
        elif k > 0:
            c = float(np.dot(imu_z[k:], rw_z[:-k]))
        else:
            c = float(np.dot(imu_z, rw_z))
        corr.append(c)
    corr = np.asarray(corr)

    best_k = int(lags[int(np.argmax(corr))])
    offset_ms = best_k * dt * 1000.0
    print(f"Estimated lag: {best_k} frames => {offset_ms:.1f} ms")
    print("Interpretation: shift IMU forward by this amount to align with wrist speed on the host timeline.")

    plt.figure()
    plt.plot(t, rw_s, label="R wrist speed (m/s, EMA)")
    plt.plot(t, imu_s / 100.0, label="IMU intensity (cm/s scaled, EMA)")
    plt.xlabel("t (s)")
    plt.title("Signals")
    plt.legend()

    plt.figure()
    plt.plot(lags * dt * 1000.0, corr)
    plt.xlabel("lag (ms)")
    plt.title("Cross-correlation")

    plt.show()


if __name__ == "__main__":
    main()
