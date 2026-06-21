"""Track game state across moves and verify consistency via partial diff.

Interface:
    GameState
"""


class GameState:
    def __init__(self):
        self.last_fen = None
        self.move_count = 0

    def update(self, fen):
        pass

    def verify_move(self, prev_fen, new_fen, move_uci):
        """Check that only the expected squares changed."""
        pass
