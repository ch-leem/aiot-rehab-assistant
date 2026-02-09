from collections import deque
from typing import Deque, Tuple, List
import numpy as np

from .ui_primitives import make_panel, plot_timeseries


class TimeseriesPanel:
    def __init__(
        self,
        w: int,
        h: int,
        title: str,
        y_label: str,
        y_min: float,
        y_max: float,
        color_bgr: Tuple[int, int, int],
    ):
        self.w = int(w)
        self.h = int(h)
        self.title = str(title)
        self.y_label = str(y_label)
        self.y_min = float(y_min)
        self.y_max = float(y_max)
        self.color_bgr = tuple(int(x) for x in color_bgr)

        self.img = make_panel(self.w, self.h, bg=22)

    def render(self, ts: Deque[float], ys: Deque[float]) -> np.ndarray:
        ts_list: List[float] = list(ts)
        ys_list: List[float] = list(ys)
        plot_timeseries(
            self.img,
            ts_list,
            ys_list,
            title=self.title,
            y_label=self.y_label,
            color_line_bgr=self.color_bgr,
            y_min=self.y_min,
            y_max=self.y_max,
        )
        return self.img
