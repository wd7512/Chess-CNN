import os
import sys

import chess
import pytest

OPENING_BOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "baron30.bin"
)


@pytest.fixture(scope="module", autouse=True)
def check_book():
    if not os.path.exists(OPENING_BOOK_PATH):
        pytest.skip(f"Opening book not found at {OPENING_BOOK_PATH}")


from chess_agent.engine_client import pick_move


class TestPickMove:
    def test_returns_valid_uci_for_starting_position(self):
        move = pick_move(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            is_white=True,
        )
        assert isinstance(move, str)
        assert len(move) >= 4
        assert move[:2] != move[2:4]

    def test_returns_legal_move(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        move_uci = pick_move(fen, is_white=True)
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        assert move in board.legal_moves

    def test_finds_checkmate(self):
        fen = "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4"
        move_uci = pick_move(fen, is_white=True)
        board = chess.Board(fen)
        board.push(chess.Move.from_uci(move_uci))
        assert board.is_checkmate()

    def test_plays_as_black(self):
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        move_uci = pick_move(fen, is_white=False)
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        assert move in board.legal_moves

    def test_empty_board_raises(self):
        fen = "8/8/8/8/8/8/8/8 w - - 0 1"
        with pytest.raises(RuntimeError, match="no move"):
            pick_move(fen, is_white=True)

    def test_castling_rights_cleared(self):
        fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
        move_uci = pick_move(fen, is_white=True)
        assert move_uci != "e1g1"
        assert move_uci != "e1c1"
