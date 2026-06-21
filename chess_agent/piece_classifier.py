import cv2
import numpy as np
import tensorflow as tf

LABELS = {0: '-', 1: 'B', 2: 'K', 3: 'N', 4: 'P', 5: 'Q', 6: 'R',
          7: 'b', 8: 'k', 9: 'n', 10: 'p', 11: 'q', 12: 'r'}


def one_hot_to_label(arr):
    return LABELS[np.argmax(arr)]


class PieceClassifier:
    def __init__(self, model_path):
        self.model = tf.keras.models.load_model(model_path)

    def classify(self, tiles):
        if len(tiles) != 64:
            raise ValueError(f"Expected 64 tiles, got {len(tiles)}")
        processed = []
        for tile in tiles:
            if tile.ndim == 3:
                tile = cv2.cvtColor(tile, cv2.COLOR_RGB2GRAY)
            processed.append(tile.astype(np.float32) / 255.0)

        inputs = np.array(processed).reshape(-1, 25, 25, 1)
        preds = self.model.predict(inputs, verbose=0)
        return [one_hot_to_label(p) for p in preds]
