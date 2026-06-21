"""Tests for FEN conversion utilities (prepare_fen, undo_prepare_fen, one_hot_to_label).

These are pure functions extracted from src.py for testability.
"""
import chess
import pytest


# --- Functions under test (extracted from src.py) ---

def prepare_fen(fen):
    """Convert FEN string to list of piece symbols. '_' separates turn."""
    fen, col = fen.split("_")
    output_arr = []
    for char in fen:
        if char.isdigit():
            output_arr += ["-"] * int(char)
        elif char == "/":
            continue
        else:
            output_arr.append(char)
    return output_arr


def undo_prepare_fen(arr):
    """Convert list of 64 piece symbols back to FEN string."""
    board = chess.Board("8/8/8/8/8/8/8/8")
    arr_rev = [arr[i:i+8] for i in range(0, 64, 8)][::-1]
    flat = []
    for row in arr_rev:
        flat.extend(row)
    for i, square in enumerate(chess.SQUARES):
        if flat[i] != "-":
            board.set_piece_at(square, chess.Piece.from_symbol(flat[i]))
    return board.fen().split(" ")[0]


def one_hot_to_label(arr):
    """Convert one-hot encoded prediction to piece symbol."""
    labels = {
        0: '-', 1: 'B', 2: 'K', 3: 'N', 4: 'P', 5: 'Q', 6: 'R',
        7: 'b', 8: 'k', 9: 'n', 10: 'p', 11: 'q', 12: 'r'
    }
    return labels[arr.index(max(arr))]


# --- Tests ---

class TestPrepareFen:
    def test_starting_position(self):
        """Standard starting FEN parsed correctly."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR_w"
        result = prepare_fen(fen)
        assert len(result) == 64
        assert result[0] == 'r'  # a8
        assert result[4] == 'k'  # e8
        assert result[63] == 'R'  # h1
        assert result[27] == '-'  # d4 (empty)

    def test_empty_board(self):
        """All empty squares."""
        fen = "8/8/8/8/8/8/8/8_w"
        result = prepare_fen(fen)
        assert all(s == '-' for s in result)

    def test_mixed_position(self):
        """Position with pieces and empty squares."""
        fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R_w"
        result = prepare_fen(fen)
        assert len(result) == 64
        assert result[0] == 'r'
        assert result[5] == 'b'  # c8 (after b-file rook moved)

    def test_turn_extraction_black(self):
        """Black turn is extracted from FEN."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR_b"
        fen_part, col = fen.split("_")
        assert col == 'b'


class TestUndoPrepareFen:
    def test_roundtrip_starting_position(self):
        """prepare_fen → undo_prepare_fen roundtrip preserves piece placement."""
        original = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR_w"
        fen_part = original.split("_")[0]
        arr = prepare_fen(original)
        result = undo_prepare_fen(arr)
        assert result == fen_part

    def test_roundtrip_complex_position(self):
        """Roundtrip with a complex middlegame position."""
        original = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R_w"
        fen_part = original.split("_")[0]
        arr = prepare_fen(original)
        result = undo_prepare_fen(arr)
        assert result == fen_part

    def test_empty_board(self):
        """Empty board roundtrip."""
        original = "8/8/8/8/8/8/8/8_w"
        arr = prepare_fen(original)
        result = undo_prepare_fen(arr)
        assert result == "8/8/8/8/8/8/8/8"

    def test_single_piece(self):
        """Board with one piece."""
        arr = ["-"] * 64
        arr[28] = 'P'  # e4
        result = undo_prepare_fen(arr)
        assert "P" in result

    def test_output_is_valid_fen(self):
        """Output can be parsed by python-chess."""
        original = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR_w"
        arr = prepare_fen(original)
        result = undo_prepare_fen(arr)
        # Should not raise
        board = chess.Board(result + " w - - 0 1")
        assert board is not None


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
        """Each index maps to the correct label."""
        expected = ['-', 'B', 'K', 'N', 'P', 'Q', 'R', 'b', 'k', 'n', 'p', 'q', 'r']
        for i, label in enumerate(expected):
            vec = [0] * 13
            vec[i] = 1
            assert one_hot_to_label(vec) == label
