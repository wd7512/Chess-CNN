"""Shared fixtures for Chess-CNN tests."""
import chess
import pytest


@pytest.fixture
def starting_board():
    """Standard starting position."""
    return chess.Board()


@pytest.fixture
def empty_board():
    """Empty board."""
    return chess.Board(fen=None)


@pytest.fixture
def checkmate_position():
    """Scholar's mate position — white to move, Qh5# is checkmate."""
    # 1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6?? 4. Qxf7#
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    board.push_san("Qh5")
    board.push_san("Nc6")
    board.push_san("Bc4")
    board.push_san("Nf6")
    return board


@pytest.fixture
def checkmate_move():
    """Qxf7# — the checkmate move in the scholar's mate position."""
    return chess.Move.from_uci("f7f5")  # Will be overridden by position


@pytest.fixture
def stalemate_position():
    """A stalemate position — black to move, no legal moves but not in check."""
    # Black king on a8, white queen on b6, white king on c8 — black to move = stalemate
    board = chess.Board("k7/8/KQ6/8/8/8/8/8 b - - 0 1")
    return board


@pytest.fixture
def castling_position():
    """Position where both sides can castle."""
    board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
    return board


@pytest.fixture
def en_passant_position():
    """Position where en passant is available."""
    # White pawn on e5, black plays d7-d5, white can capture en passant
    board = chess.Board("8/8/8/3Pp3/8/8/8/8 w - e6 0 1")
    return board


@pytest.fixture
def board_coords():
    """Standard board coordinates for click math tests."""
    return {"x": 100, "y": 200, "w": 400, "h": 400}
