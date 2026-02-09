import math
import numpy as np

# =========================
# One Euro Filter (3D)
# =========================
class OneEuroFilter1D:
    def __init__(self, min_cutoff=1.5, beta=0.02, d_cutoff=1.0, max_delta_per_sec=None):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.max_delta_per_sec = None if max_delta_per_sec is None else float(max_delta_per_sec)
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    @staticmethod
    def _alpha(cutoff_hz: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff_hz)
        return 1.0 / (1.0 + tau / max(dt, 1e-6))

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def __call__(self, x: float, t: float) -> float:
        if self.t_prev is None or self.x_prev is None:
            self.t_prev = t
            self.x_prev = float(x)
            self.dx_prev = 0.0
            return float(x)

        dt = max(t - self.t_prev, 1e-6)
        x = float(x)

        # Clamp single-frame jumps before OneEuro update to suppress depth spikes.
        if self.max_delta_per_sec is not None and self.max_delta_per_sec > 0.0:
            max_delta = self.max_delta_per_sec * dt
            dx_raw = x - self.x_prev
            if abs(dx_raw) > max_delta:
                x = self.x_prev + math.copysign(max_delta, dx_raw)

        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)

        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat

class OneEuroFilter3D:
    def __init__(self, min_cutoff=1.5, beta=0.02, d_cutoff=1.0, z_max_delta_per_sec=2.0):
        self.fx = OneEuroFilter1D(min_cutoff, beta, d_cutoff)
        self.fy = OneEuroFilter1D(min_cutoff, beta, d_cutoff)
        self.fz = OneEuroFilter1D(min_cutoff, beta, d_cutoff, max_delta_per_sec=z_max_delta_per_sec)

    def reset(self):
        self.fx.reset()
        self.fy.reset()
        self.fz.reset()

    def __call__(self, xyz: np.ndarray, t: float) -> np.ndarray:
        x, y, z = float(xyz[0]), float(xyz[1]), float(xyz[2])
        return np.array([self.fx(x, t), self.fy(y, t), self.fz(z, t)], dtype=np.float32)
