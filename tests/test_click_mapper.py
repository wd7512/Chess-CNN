import pytest
from chess_agent.click_mapper import uci_to_pixels


class TestWhitePerspective:
    def test_e2e4(self):
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 400}
        sx, sy, ex, ey = uci_to_pixels("e2e4", rect, is_white=True)
        sq = 50
        assert sx == 100 + 4.5 * sq
        assert sy == 200 + 6.5 * sq
        assert ex == 100 + 4.5 * sq
        assert ey == 200 + 4.5 * sq

    def test_a1h8(self):
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 400}
        sx, sy, ex, ey = uci_to_pixels("a1h8", rect, is_white=True)
        sq = 50
        assert sx == 100 + 0.5 * sq
        assert sy == 200 + 7.5 * sq
        assert ex == 100 + 7.5 * sq
        assert ey == 200 + 0.5 * sq

    def test_clicks_within_bounds(self):
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 400}
        for move in ["e2e4", "g1f3", "d2d4", "e1g1"]:
            sx, sy, ex, ey = uci_to_pixels(move, rect, is_white=True)
            assert rect['x'] <= sx <= rect['x'] + rect['w']
            assert rect['y'] <= sy <= rect['y'] + rect['h']
            assert rect['x'] <= ex <= rect['x'] + rect['w']
            assert rect['y'] <= ey <= rect['y'] + rect['h']


class TestBlackPerspective:
    def test_e7e5_symmetry(self):
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 400}
        _, b_sy, _, _ = uci_to_pixels("e7e5", rect, is_white=False)
        assert b_sy < 200 + 400 // 2

    def test_horizontal_flip(self):
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 400}
        w_sx, _, _, _ = uci_to_pixels("a1a1", rect, is_white=True)
        b_sx, _, _, _ = uci_to_pixels("a8a8", rect, is_white=False)
        assert w_sx < 100 + 200
        assert b_sx > 100 + 200

    def test_clicks_within_bounds(self):
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 400}
        for move in ["e7e5", "g8f6", "d7d5", "e8g8"]:
            sx, sy, ex, ey = uci_to_pixels(move, rect, is_white=False)
            assert rect['x'] <= sx <= rect['x'] + rect['w']
            assert rect['y'] <= sy <= rect['y'] + rect['h']
            assert rect['x'] <= ex <= rect['x'] + rect['w']
            assert rect['y'] <= ey <= rect['y'] + rect['h']

    def test_non_square_board_uses_height(self):
        rect = {'x': 100, 'y': 200, 'w': 400, 'h': 480}
        _, _, _, ey = uci_to_pixels("e7e5", rect, is_white=False)
        sq = ((400 + 480) // 2) // 8
        expected_ey = 200 + 480 - (5 - 1 + 0.5) * sq
        assert abs(ey - expected_ey) < 1

    def test_accepts_width_height_keys(self):
        rect = {'x': 100, 'y': 200, 'width': 400, 'height': 400}
        b_sx, _, _, _ = uci_to_pixels("a8a8", rect, is_white=False)
        assert b_sx > 100 + 200


class TestEdgeCases:
    def test_promotion_to_queen(self):
        rect = {'x': 0, 'y': 0, 'w': 400, 'h': 400}
        sx, sy, ex, ey = uci_to_pixels("e7e8q", rect, is_white=True)
        sq = 50
        assert sx == 4.5 * sq
        assert sy == 1.5 * sq
        assert ex == 4.5 * sq
        assert ey == 0.5 * sq

    def test_castling_kingside(self):
        rect = {'x': 0, 'y': 0, 'w': 400, 'h': 400}
        sx, sy, ex, ey = uci_to_pixels("e1g1", rect, is_white=True)
        sq = 50
        assert sx == 4.5 * sq
        assert sy == 7.5 * sq
        assert ex == 6.5 * sq
        assert ey == 7.5 * sq
