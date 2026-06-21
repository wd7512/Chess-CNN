"""Interface to the minimax chess engine.

Wraps Intermediate_Engines.min_maxN_pruned with root-only book lookup.
Interface:
    pick_move(fen: str, is_white: bool) -> str
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Intermediate_Engines import min_maxN_pruned
import chess


def pick_move(fen, is_white):
    """Pick the best move for the given FEN position. Returns UCI string."""
    pass
