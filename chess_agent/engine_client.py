import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Intermediate_Engines import min_maxN_pruned
import chess


def pick_move(fen, is_white):
    board = chess.Board(fen)
    board.castling_rights = chess.BB_EMPTY
    board.turn = is_white
    move = min_maxN_pruned(board, 3, is_root=True)
    if move is None:
        raise RuntimeError("Engine returned no move for position")
    return move.uci()
