from typing import Tuple
import numpy as np
import cv2

from .ui_primitives import make_panel, draw_card


def compose_three_panel(
    left_img: np.ndarray,
    top_img: np.ndarray,
    bottom_img: np.ndarray,
    win_w: int,
    win_h: int,
    left_w: int,
) -> np.ndarray:
    win_w = int(win_w)
    win_h = int(win_h)
    left_w = int(left_w)

    canvas = make_panel(win_w, win_h, bg=16)

    left = canvas[:, :left_w]
    right = canvas[:, left_w:]

    slot_w = left_w - 40
    slot_h = win_h - 40
    im_left = cv2.resize(left_img, (slot_w, slot_h), interpolation=cv2.INTER_AREA)

    draw_card(left, 10, 10, left_w - 10, win_h - 10, radius=18)
    left[20:win_h - 20, 20:left_w - 20] = im_left

    rh, rw = right.shape[:2]
    top = right[:rh // 2, :]
    bot = right[rh // 2:, :]

    top[:, :] = cv2.resize(top_img, (rw, rh // 2), interpolation=cv2.INTER_AREA)
    bot[:, :] = cv2.resize(bottom_img, (rw, rh - rh // 2), interpolation=cv2.INTER_AREA)

    return canvas
