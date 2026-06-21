"""Read-only Playwright DOM queries against the Lichess game page.

Interface:
    DOMReader(page: playwright.sync_api.Page)
"""


class DOMReader:
    def __init__(self, page):
        self.page = page

    def get_board_rect(self):
        """Return {x, y, w, h} of the board element."""
        pass

    def get_orientation(self):
        """Return 'white' or 'black'."""
        pass

    def is_our_turn(self, our_color):
        """Check if the running clock matches our color."""
        pass

    def get_selected_square(self):
        """Return the selected square's coordinates or None."""
        pass

    def get_last_move_squares(self):
        """Return list of squares with last-move class."""
        pass

    def has_game_over_dialog(self):
        pass

    def dismiss_overlays(self):
        """Close any blocking popups (draw offers, etc.)."""
        pass

    def get_game_result(self):
        """Return the game result string if game is over."""
        pass
