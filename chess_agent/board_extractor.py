"""Extract board tiles from a screenshot using the board bounding rect.

Pure OpenCV — no Playwright dependency.
Interface:
    crop_board(image: np.ndarray, rect: dict) -> np.ndarray
    split_tiles(board_200: np.ndarray) -> list[np.ndarray]
"""

import cv2
import numpy as np


def crop_board(image, rect, margin=2):
    """Crop the board region from a full-page screenshot."""
    pass


def split_tiles(board_200):
    """Split a 200x200 board image into 64 25x25 tiles."""
    pass
