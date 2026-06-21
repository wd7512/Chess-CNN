"""Page state machine and lifecycle management.

Handles: login detection, lobby/game/game_over states, turn waiting,
board stability polling, heartbeat checks.
"""


class PageManager:
    def __init__(self, page, dom_reader, our_color):
        self.page = page
        self.dom_reader = dom_reader
        self.our_color = our_color

    def detect_state(self):
        """Return one of: 'login', 'lobby', 'game', 'game_over'."""
        pass

    def navigate_to_game(self, game_url):
        pass

    def wait_for_turn(self, timeout=60):
        """Block until it's our turn or timeout. Returns True if our turn."""
        pass

    def is_board_stable(self):
        """Check that no CSS animations are running on the board."""
        pass

    def wait_for_board_stability(self, timeout_ms=2000):
        pass

    def heartbeat_check(self):
        """Verify WebSocket/connection is still alive."""
        pass
