"""CNN-based chess piece classifier.

Wraps the trained Piece_Classifier.h5 model.
Interface:
    classify(tiles: list[np.ndarray]) -> list[str]
"""

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
        """Classify 64 tiles. Returns list of 64 piece labels."""
        pass
