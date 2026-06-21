"""Click actions and move verification on the Lichess game page.

Interface:
    DOMActor(page, dom_reader: DOMReader)
"""


class DOMActor:
    def __init__(self, page, dom_reader):
        self.page = page
        self.dom_reader = dom_reader

    def click_square(self, uci_square):
        """Click a square by UCI coordinate (e.g. 'e2')."""
        pass

    def click_move(self, uci):
        """Click source then dest for a UCI move. Returns True if verified."""
        pass

    def verify_move_made(self, uci, previous_fen):
        """Check that the board state changed as expected after clicking."""
        pass
