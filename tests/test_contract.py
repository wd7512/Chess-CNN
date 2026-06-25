"""Contract tests — verify data format compatibility between adjacent components.

Each test validates that the output of one component satisfies the input
contract of the next component in the pipeline.

Pipeline: board_extractor → piece_classifier → fen_assembler → engine_client → click_mapper → dom_actor
"""
import cv2
import numpy as np
import pytest
from chess_agent.board_extractor import crop_board, split_tiles
from chess_agent.click_mapper import uci_to_pixels
from chess_agent.fen_assembler import labels_to_fen
from chess_agent.piece_classifier import one_hot_to_label
from chess_agent.config import PIECE_CLASSIFIER_PATH

LABELS = {0: '-', 1: 'B', 2: 'K', 3: 'N', 4: 'P', 5: 'Q', 6: 'R',
          7: 'b', 8: 'k', 9: 'n', 10: 'p', 11: 'q', 12: 'r'}
LABEL_CHARS = set('-KkQqRrBbNnPp')


def _build_test_board(grayscale=True):
    """Build a 400×400 board image with 8×8 checkerboard pattern."""
    h, w = 400, 400
    if grayscale:
        img = np.full((h, w), 128, dtype=np.uint8)
    else:
        img = np.full((h, w, 3), (128, 128, 128), dtype=np.uint8)
    sq = 50
    for r in range(8):
        for c in range(8):
            y, x = r * sq, c * sq
            if (r + c) % 2 == 0:
                color = 200 if grayscale else (200, 200, 200)
                img[y:y+sq, x:x+sq] = color
    return img


class TestBoardExtractorToPieceClassifier:
    """board_extractor output → piece_classifier input contract."""

    def test_crop_board_output_is_valid_image(self):
        img = _build_test_board()
        rect = {"x": 0, "y": 0, "w": 400, "h": 400}
        cropped = crop_board(img, rect)
        assert isinstance(cropped, np.ndarray)
        assert cropped.ndim in (2, 3)

    def test_crop_resize_produces_200x200(self):
        img = _build_test_board()
        rect = {"x": 0, "y": 0, "w": 400, "h": 400}
        cropped = crop_board(img, rect)
        resized = cv2.resize(cropped, (200, 200))
        assert resized.shape[:2] == (200, 200)

    def test_split_tiles_returns_64_tiles_25x25(self):
        board = np.zeros((200, 200), dtype=np.uint8)
        tiles = split_tiles(board)
        assert len(tiles) == 64
        for i, tile in enumerate(tiles):
            assert tile.shape == (25, 25), f"Tile {i} has shape {tile.shape}"
            assert tile.dtype == np.uint8

    def test_tiles_path_to_classifier(self):
        board = np.zeros((200, 200), dtype=np.uint8)
        tiles = split_tiles(board)
        for tile in tiles:
            processed = tile.astype(np.float32) / 255.0
            shaped = processed.reshape(25, 25, 1)
            assert shaped.shape == (25, 25, 1)
            assert 0.0 <= shaped.min() <= shaped.max() <= 1.0


class TestPieceClassifierToFenAssembler:
    """piece_classifier output → fen_assembler input contract."""

    def test_labels_are_64_strings_from_valid_set(self):
        labels = ['-'] * 64
        assert len(labels) == 64
        for label in labels:
            assert isinstance(label, str)
            assert label in LABEL_CHARS
        fen = labels_to_fen(labels)
        assert isinstance(fen, str)
        assert len(fen) > 0
        assert '/' in fen

    def test_one_hot_to_label_produces_valid_symbol(self):
        for idx, expected in LABELS.items():
            vec = [0.0] * 13
            vec[idx] = 1.0
            label = one_hot_to_label(vec)
            assert label == expected
            assert label in LABEL_CHARS

    def test_classifier_output_feeds_fen_assembler(self):
        labels = [
            'r', 'n', 'b', 'q', 'k', 'b', 'n', 'r',
            'p', 'p', 'p', 'p', 'p', 'p', 'p', 'p',
            '-', '-', '-', '-', '-', '-', '-', '-',
            '-', '-', '-', '-', '-', '-', '-', '-',
            '-', '-', '-', '-', '-', '-', '-', '-',
            '-', '-', '-', '-', '-', '-', '-', '-',
            'P', 'P', 'P', 'P', 'P', 'P', 'P', 'P',
            'R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R',
        ]
        fen = labels_to_fen(labels)
        assert fen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        assert isinstance(fen, str)
        assert all(c in 'KkQqRrBbNnPp12345678/-' for c in fen)


class TestFenAssemblerToEngineClient:
    """fen_assembler output → engine_client input contract."""

    def test_labels_to_fen_produces_valid_placement(self):
        labels = ['-'] * 64
        labels[0] = 'k'
        labels[63] = 'K'
        fen = labels_to_fen(labels)
        assert isinstance(fen, str)
        assert fen.count('/') == 7
        ranks = fen.split('/')
        assert len(ranks) == 8
        for rank in ranks:
            total = sum(int(c) if c.isdigit() else 1 for c in rank)
            assert total == 8, f"Rank '{rank}' sums to {total}"

    def test_placement_is_compatible_with_chess_fen(self):
        import chess
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        board = chess.Board(fen + " w KQkq - 0 1")
        assert board.is_valid()


class TestEngineClientToClickMapper:
    """engine_client output → click_mapper input contract."""

    def test_uci_move_is_valid_format(self):
        moves = ["e2e4", "e7e5", "g1f3", "b8c6", "e1g1", "e8g8", "e7e8q"]
        for uci in moves:
            assert isinstance(uci, str)
            assert 4 <= len(uci) <= 5
            assert uci[0].isalpha() and uci[0].islower()
            assert uci[1].isdigit()
            assert uci[2].isalpha() and uci[2].islower()
            assert uci[3].isdigit()
            if len(uci) == 5:
                assert uci[4] == 'q'

    def test_uci_parses_with_chess_lib(self):
        import chess
        for uci in ["e2e4", "e7e5", "g1f3", "e1g1", "e7e8q"]:
            move = chess.Move.from_uci(uci)
            assert chess.square_name(move.from_square) == uci[:2]
            assert chess.square_name(move.to_square) == uci[2:4]


class TestClickMapperToDomActor:
    """click_mapper output → dom_actor input contract."""

    def test_uci_to_pixels_returns_coords_in_bounds(self):
        rect = {"x": 100, "y": 200, "w": 400, "h": 400}
        moves = ["e2e4", "e7e5", "g1f3", "b8c6", "e1g1", "e7e8q"]
        for uci in moves:
            sx, sy, ex, ey = uci_to_pixels(uci, rect, is_white=True)
            assert rect["x"] <= sx <= rect["x"] + rect["w"]
            assert rect["y"] <= sy <= rect["y"] + rect["h"]
            assert rect["x"] <= ex <= rect["x"] + rect["w"]
            assert rect["y"] <= ey <= rect["y"] + rect["h"]

    def test_clickable_coords_for_both_orientations(self):
        rect = {"x": 100, "y": 200, "w": 400, "h": 400}
        w_sx, w_sy, w_ex, w_ey = uci_to_pixels("e2e4", rect, is_white=True)
        b_sx, b_sy, b_ex, b_ey = uci_to_pixels("e7e5", rect, is_white=False)
        assert all(isinstance(v, (int, float)) for v in (w_sx, w_sy, w_ex, w_ey, b_sx, b_sy, b_ex, b_ey))
        assert (w_sx, w_sy, w_ex, w_ey) != (b_sx, b_sy, b_ex, b_ey)

    def test_coords_are_monotonic_with_board_rect(self):
        rect = {"x": 100, "y": 200, "w": 400, "h": 400}
        sx, sy, ex, ey = uci_to_pixels("a1h8", rect, is_white=True)
        assert sx < ex
        assert sy > ey


class TestFullPipelineBoundary:
    """End-to-end contract: synthetic data flows through all components."""

    def test_synthetic_pipeline_shapes(self):
        board = np.zeros((200, 200), dtype=np.uint8)
        tiles = split_tiles(board)
        assert len(tiles) == 64
        assert all(t.shape == (25, 25) for t in tiles)

        processed = np.array([t.astype(np.float32) / 255.0 for t in tiles]).reshape(-1, 25, 25, 1)
        assert processed.shape == (64, 25, 25, 1)
        assert processed.dtype == np.float32

    def test_fen_assembler_output_accepts_active_color(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        import chess
        for turn in ["w", "b"]:
            full = f"{fen} {turn} KQkq - 0 1"
            board = chess.Board(full)
            assert board.turn == (turn == "w")

    def test_uci_pixels_stays_within_board_for_various_rects(self):
        rects = [
            {"x": 0, "y": 0, "w": 400, "h": 400},
            {"x": 100, "y": 100, "w": 480, "h": 480},
            {"x": 50, "y": 75, "w": 350, "h": 420},
        ]
        for rect in rects:
            sx, sy, ex, ey = uci_to_pixels("e2e4", rect, is_white=True)
            assert rect["x"] <= sx <= rect["x"] + rect["w"]
            assert rect["y"] <= sy <= rect["y"] + rect["h"]
            assert rect["x"] <= ex <= rect["x"] + rect["w"]
            assert rect["y"] <= ey <= rect["y"] + rect["h"]
