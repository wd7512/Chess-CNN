"""Tests for click coordinate calculation (white and black perspective).

These test the coordinate math extracted from src.py lines 198-209.
The black perspective formula has a known bug (y+w instead of y+h, wrong rank flip).
"""
import pytest


# --- Functions under test (extracted from src.py) ---

def get_click_coords_white(move_uci, x, y, w, h):
    """Calculate click coordinates for white perspective (from src.py lines 198-203)."""
    square_size = ((w + h) // 2) // 8
    start_x = x + (ord(move_uci[0]) - 97 + 0.5) * square_size
    start_y = y + (8 - int(move_uci[1]) + 0.5) * square_size
    end_x = x + (ord(move_uci[2]) - 97 + 0.5) * square_size
    end_y = y + (8 - int(move_uci[3]) + 0.5) * square_size
    return (start_x, start_y, end_x, end_y)


def get_click_coords_black(move_uci, x, y, w, h):
    """Calculate click coordinates for black perspective (from src.py lines 205-209).

    BUG: Uses 'w' instead of 'h' for vertical offset, and the rank flip formula
    (8 - rank + 0.5) is wrong — should be (rank - 1 + 0.5).
    """
    square_size = ((w + h) // 2) // 8
    start_x = x + w - (ord(move_uci[0]) - 97 + 0.5) * square_size
    start_y = y + w - (8 - int(move_uci[1]) + 0.5) * square_size  # BUG: w should be h
    end_x = x + w - (ord(move_uci[2]) - 97 + 0.5) * square_size
    end_y = y + w - (8 - int(move_uci[3]) + 0.5) * square_size      # BUG: w should be h
    return (start_x, start_y, end_x, end_y)


# --- Tests ---

class TestClickCoordsWhite:
    """White perspective click math — should be correct."""

    def test_e2e4(self, board_coords):
        """e2e4: pawn from e2 to e4."""
        x, y, w, h = board_coords["x"], board_coords["y"], board_coords["w"], board_coords["h"]
        sx, sy, ex, ey = get_click_coords_white("e2e4", x, y, w, h)
        sq = 50  # 400/8
        # e2: file e (index 4), rank 2 → y offset = (8-2+0.5)*50 = 325
        assert sx == x + 4.5 * sq  # 100 + 225 = 325
        assert sy == y + 6.5 * sq  # 200 + 325 = 525
        # e4: file e (index 4), rank 4 → y offset = (8-4+0.5)*50 = 225
        assert ex == x + 4.5 * sq  # 325
        assert ey == y + 4.5 * sq  # 200 + 225 = 425

    def test_a1h8(self, board_coords):
        """a1h8: diagonal from corner to corner."""
        x, y, w, h = board_coords["x"], board_coords["y"], board_coords["w"], board_coords["h"]
        sx, sy, ex, ey = get_click_coords_white("a1h8", x, y, w, h)
        sq = 50
        # a1: file a (0), rank 1 → y offset = (8-1+0.5)*50 = 375
        assert sx == x + 0.5 * sq  # 125
        assert sy == y + 7.5 * sq  # 575
        # h8: file h (7), rank 8 → y offset = (8-8+0.5)*50 = 25
        assert ex == x + 7.5 * sq  # 475
        assert ey == y + 0.5 * sq  # 225

    def test_center_squares(self, board_coords):
        """d4d5: center pawn push."""
        x, y, w, h = board_coords["x"], board_coords["y"], board_coords["w"], board_coords["h"]
        sx, sy, ex, ey = get_click_coords_white("d4d5", x, y, w, h)
        sq = 50
        assert sx == x + 3.5 * sq
        assert sy == y + 4.5 * sq
        assert ex == x + 3.5 * sq
        assert ey == y + 3.5 * sq

    def test_clicks_within_bounds(self, board_coords):
        """All clicks should land within the board region."""
        x, y, w, h = board_coords["x"], board_coords["y"], board_coords["w"], board_coords["h"]
        for move in ["e2e4", "g1f3", "d2d4", "e1g1"]:
            sx, sy, ex, ey = get_click_coords_white(move, x, y, w, h)
            assert x <= sx <= x + w, f"start_x {sx} out of bounds for {move}"
            assert y <= sy <= y + h, f"start_y {sy} out of bounds for {move}"
            assert x <= ex <= x + w, f"end_x {ex} out of bounds for {move}"
            assert y <= ey <= y + h, f"end_y {ey} out of bounds for {move}"


class TestClickCoordsBlack:
    """Black perspective click math — tests should FAIL due to known bug.

    The bug: uses y+w instead of y+h, and the rank flip formula is inverted.
    After fixing, these tests should pass.
    """

    def test_e7e5_symmetry(self, board_coords):
        """e7e5 from black's view should mirror e2e4 from white's view.

        From black's perspective, e7 is near the bottom of the screen
        (black's 2nd rank = white's 7th rank from top).
        """
        x, y, w, h = board_coords["x"], board_coords["y"], board_coords["w"], board_coords["h"]
        sq = 50

        # White e2e4: start near bottom-left area, end near center
        w_sx, w_sy, w_ex, w_ey = get_click_coords_white("e2e4", x, y, w, h)

        # Black e7e5: should be the mirror — start near top-right area (from white's view)
        b_sx, b_sy, b_ex, b_ey = get_click_coords_black("e7e5", x, y, w, h)

        # The start of black e7 should be at the same x as white e2 (same file)
        # but at the opposite y (rank 7 from top vs rank 2 from top)
        # Expected: b_sx ≈ w_sx (same file e), b_sy should be near top (rank 7)

        # With the bug, b_sy = y + w - (8-7+0.5)*sq = y + 400 - 75 = y + 325
        # This is near the BOTTOM of the board, not the top — WRONG
        # Expected: b_sy = y + h - (7-1+0.5)*sq = y + 400 - 325 = y + 75 (near top)

        # This assertion will FAIL with the buggy code:
        assert b_sy < y + h // 2, (
            f"Black e7 start_y={b_sy} should be in top half of board (rank 7), "
            f"but it's in bottom half. Bug: rank flip formula is inverted."
        )

    def test_black_flip_symmetry(self, board_coords):
        """Black's a8 should map to white's h1 position (180-degree rotation)."""
        x, y, w, h = board_coords["x"], board_coords["y"], board_coords["w"], board_coords["h"]

        # White h1 click
        w_sx, w_sy, _, _ = get_click_coords_white("h1a1", x, y, w, h)

        # Black a8 click — should be near white h1 after 180-degree flip
        b_sx, b_sy, _, _ = get_click_coords_black("a8h8", x, y, w, h)

        # After 180-degree rotation, black's a8 (top-left from their view)
        # should be near white's h1 (bottom-right from white's view)
        # Allow 1 square tolerance
        sq = 50
        assert abs(b_sx - w_sx) < sq, (
            f"Black a8 x={b_sx} should be near white h1 x={w_sx}"
        )
        assert abs(b_sy - w_sy) < sq, (
            f"Black a8 y={b_sy} should be near white h1 y={w_sy}"
        )

    def test_black_clicks_within_bounds(self, board_coords):
        """All black clicks should land within the board region."""
        x, y, w, h = board_coords["x"], board_coords["y"], board_coords["w"], board_coords["h"]
        for move in ["e7e5", "g8f6", "d7d5", "e8g8"]:
            sx, sy, ex, ey = get_click_coords_black(move, x, y, w, h)
            assert x <= sx <= x + w, f"start_x {sx} out of bounds for {move}"
            assert y <= sy <= y + h, f"start_y {sy} out of bounds for {move}"
            assert x <= ex <= x + w, f"end_x {ex} out of bounds for {move}"
            assert y <= ey <= y + h, f"end_y {ey} out of bounds for {move}"

    def test_non_square_board_uses_height(self):
        """When w != h, vertical offset should use h, not w."""
        # Board at x=100, y=200, w=400, h=480 (non-square)
        x, y, w, h = 100, 200, 400, 480
        sq = ((w + h) // 2) // 8  # = 55

        sx, sy, ex, ey = get_click_coords_black("e7e5", x, y, w, h)

        # The vertical offset should be based on h=480, not w=400
        # Expected start_y for rank 7: y + h - (7-1+0.5)*sq = 200 + 480 - 357.5 = 322.5
        # Buggy: y + w - (8-7+0.5)*sq = 200 + 400 - 82.5 = 517.5
        expected_sy = y + h - (7 - 1 + 0.5) * sq
        assert abs(ey - expected_sy) < 1, (
            f"Black e5 end_y={ey} should be {expected_sy} (using h={h}), "
            f"but buggy code uses w={w}"
        )
