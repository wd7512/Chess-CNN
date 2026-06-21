import pytest
from chess_agent.game_state import GameState, verify_partial_diff


class TestVerifyPartialDiff:
    def test_source_square_changed(self):
        assert verify_partial_diff(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            "e2e4",
        ) is True

    def test_dest_square_changed(self):
        assert verify_partial_diff(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            "e2e4",
        ) is True

    def test_capture(self):
        assert verify_partial_diff(
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR",
            "d7d5",
        ) is True

    def test_no_change_returns_false(self):
        assert verify_partial_diff(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "e2e4",
        ) is False

    def test_none_prev_fen_returns_true(self):
        assert verify_partial_diff(None, "8/8/8/8/8/8/8/8", "e2e4") is True

    def test_none_new_fen_returns_true(self):
        assert verify_partial_diff("8/8/8/8/8/8/8/8", None, "e2e4") is True

    def test_en_passant_capture(self):
        assert verify_partial_diff(
            "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR",
            "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR",
            "e5d6",
        ) is False


class TestGameState:
    def test_initial_state(self):
        gs = GameState()
        assert gs.last_fen is None
        assert gs.move_count == 0
        assert gs.fens == []

    def test_update(self):
        gs = GameState()
        gs.update("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
        assert gs.last_fen is not None
        assert len(gs.fens) == 1
        assert gs.move_count == 0

    def test_verify_move_delegates(self):
        gs = GameState()
        prev = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
        new = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"
        assert gs.verify_move(prev, new, "e2e4") is True
        assert gs.verify_move(prev, prev, "e2e4") is False
