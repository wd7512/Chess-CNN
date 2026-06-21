"""Main orchestrator for the vision-driven chess agent.

Runs the per-move loop:
  wait turn → screenshot → extract board → classify → FEN → engine → click → verify
"""


class ChessAgent:
    def __init__(self, game_url, our_color, cookie_path=None):
        self.game_url = game_url
        self.our_color = our_color
        self.cookie_path = cookie_path

    def run(self):
        """Main game loop. Returns game result."""
        pass

    def _shutdown(self):
        """Clean up on SIGTERM/SIGINT."""
        pass
