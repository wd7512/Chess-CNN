import os
import sys

import numpy as np
import pytest

from chess_agent.piece_classifier import PieceClassifier, one_hot_to_label

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "Models", "Piece_Classifier.h5")


@pytest.fixture(scope="module")
def classifier():
    if not os.path.exists(MODEL_PATH):
        pytest.skip(f"Model not found at {MODEL_PATH}")
    return PieceClassifier(MODEL_PATH)


def make_tile(fill_value=0):
    return np.full((25, 25), fill_value, dtype=np.uint8)


class TestOneHotToLabel:
    def test_empty_square(self):
        vec = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        assert one_hot_to_label(vec) == '-'

    def test_white_queen(self):
        vec = [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
        assert one_hot_to_label(vec) == 'Q'

    def test_black_king(self):
        vec = [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]
        assert one_hot_to_label(vec) == 'k'

    def test_all_labels(self):
        expected = ['-', 'B', 'K', 'N', 'P', 'Q', 'R', 'b', 'k', 'n', 'p', 'q', 'r']
        for i, label in enumerate(expected):
            vec = [0] * 13
            vec[i] = 1
            assert one_hot_to_label(vec) == label


class TestPieceClassifier:
    def test_classify_returns_64_labels(self, classifier):
        tiles = [make_tile(0) for _ in range(64)]
        labels = classifier.classify(tiles)
        assert len(labels) == 64

    def test_labels_are_valid_fen_chars(self, classifier):
        tiles = [make_tile(128) for _ in range(64)]
        labels = classifier.classify(tiles)
        valid = set('-KkQqRrBbNnPp')
        for label in labels:
            assert label in valid, f"Invalid label: {label}"

    def test_handles_color_tiles(self, classifier):
        tiles = [np.full((25, 25, 3), 100, dtype=np.uint8) for _ in range(64)]
        labels = classifier.classify(tiles)
        assert len(labels) == 64

    def test_wrong_number_of_tiles_raises(self, classifier):
        with pytest.raises(ValueError, match="64 tiles"):
            classifier.classify([make_tile(0)])

    def test_empty_tiles_all_dashes(self, classifier):
        tiles = [make_tile(255) for _ in range(64)]
        labels = classifier.classify(tiles)
        assert all(l == '-' for l in labels)
