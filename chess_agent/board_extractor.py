import cv2
import numpy as np


def crop_board(image, rect, margin=2):
    x = int(rect['x'])
    y = int(rect['y'])
    w = int(rect.get('w', rect.get('width', 0)))
    h = int(rect.get('h', rect.get('height', 0)))
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(image.shape[1], x + w + margin)
    y2 = min(image.shape[0], y + h + margin)
    return image[y1:y2, x1:x2]


def split_tiles(board_200):
    if board_200.shape[0] != 200 or board_200.shape[1] != 200:
        raise ValueError(f"Expected 200x200 board image, got {board_200.shape[:2]}")
    tiles = []
    for i in range(8):
        for j in range(8):
            tile = board_200[i*25:(i+1)*25, j*25:(j+1)*25]
            tiles.append(tile)
    return tiles
