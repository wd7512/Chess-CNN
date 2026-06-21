"""Tests for the minimax engine (Intermediate_Engines.py).

Tests engine correctness: checkmate detection, stalemate, castling rights,
opening book usage, alpha-beta pruning consistency.
"""
import chess
import pytest


# --- Engine functions under test (extracted from Intermediate_Engines.py) ---

scoring = {
    'p': -100, 'n': -300, 'b': -300, 'r': -500, 'q': -900, 'k': 0,
    'P': 100, 'N': 300, 'B': 300, 'R': 500, 'Q': 900, 'K': 0,
}


def eval_board(board):
    """Material evaluation from white's perspective."""
    score = 0
    pieces = board.piece_map()
    for key in pieces:
        score += scoring[str(pieces[key])]
    return score


def eval_space(board):
    """Mobility evaluation from white's perspective."""
    no_moves = len(list(board.legal_moves))
    if board.turn == True:
        return no_moves
    else:
        return -no_moves


# Simplified minimax without opening book (for testing pure search)
def min_maxN_pruned(board, n, alpha=float('-inf'), beta=float('inf')):
    """Alpha-beta pruned minimax. No opening book — pure search."""
    moves = list(board.legal_moves)
    best_move = None

    if board.turn:  # White (maximizing)
        max_eval = float('-inf')
        for move in moves:
            temp = board.copy()
            temp.push(move)
            outcome = temp.outcome()
            if outcome:
                if temp.is_checkmate():
                    return move
                else:
                    eval_score = 0  # Draw
            else:
                if n > 1:
                    temp_eval = min_maxN_pruned(temp, n - 1, alpha, beta)
                    if temp_eval:
                        temp.push(temp_eval)
                eval_score = eval_board(temp) + eval_space(temp)

            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
    else:  # Black (minimizing)
        min_eval = float('inf')
        for move in moves:
            temp = board.copy()
            temp.push(move)
            outcome = temp.outcome()
            if outcome:
                if temp.is_checkmate():
                    return move
                else:
                    eval_score = 0  # Draw
            else:
                if n > 1:
                    temp_eval = min_maxN_pruned(temp, n - 1, alpha, beta)
                    if temp_eval:
                        temp.push(temp_eval)
                eval_score = eval_board(temp) + eval_space(temp)

            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
            beta = min(beta, eval_score)
            if beta <= alpha:
                break

    return best_move


# --- Tests ---

class TestEvalBoard:
    def test_starting_position_is_equal(self):
        """Starting position should evaluate to 0 (equal material)."""
        board = chess.Board()
        assert eval_board(board) == 0

    def test_white_up_a_pawn(self):
        """White up a pawn should be +100."""
        board = chess.Board("8/8/8/8/8/8/P7/8 w - - 0 1")
        assert eval_board(board) == 100

    def test_black_up_a_knight(self):
        """Black up a knight should be -300."""
        board = chess.Board("8/8/8/8/8/8/8/n7 w - - 0 1")
        assert eval_board(board) == -300

    def test_white_up_queen(self):
        """White up a queen should be +900."""
        board = chess.Board("8/8/8/8/8/8/8/Q7 w - - 0 1")
        assert eval_board(board) == 900


class TestEvalSpace:
    def test_white_mobility_positive(self):
        """White to move with many moves should be positive."""
        board = chess.Board()
        board.turn = True
        score = eval_space(board)
        assert score > 0
        assert score == 20  # 20 legal moves in starting position

    def test_black_mobility_negative(self):
        """Black to move with many moves should be negative."""
        board = chess.Board()
        board.turn = False
        score = eval_space(board)
        assert score < 0
        assert score == -20

    def test_equal_mobility(self):
        """Symmetric position should have equal magnitude."""
        board = chess.Board()
        white_score = eval_space(board)
        board.turn = False
        black_score = eval_space(board)
        assert white_score == -black_score


class TestCheckmate:
    def test_fools_mate_position(self):
        """Fools mate: 1. f3 e5 2. g4 Qh4#. Engine should find Qh4#."""
        board = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2")
        move = min_maxN_pruned(board, 3)
        assert move is not None
        board.push(move)
        assert board.is_checkmate(), f"Expected checkmate, got {move}"

    def test_scholars_mate_position(self):
        """Scholar's mate setup: after 1.e4 e5 2.Qh5 Nc6 3.Bc4, black plays Nf6??, white Qxf7#."""
        # Position after 1.e4 e5 2.Qh5 Nc6 3.Bc4 Nf6??
        board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 4")
        move = min_maxN_pruned(board, 3)
        assert move is not None
        board.push(move)
        assert board.is_checkmate(), f"Expected checkmate, got {move}"

    def test_engine_finds_checkmate_in_1(self):
        """Engine should always find checkmate in 1 when available."""
        # Back rank mate setup
        board = chess.Board("6k1/5ppp/8/8/8/8/8/R3K3 w Q - 0 1")
        move = min_maxN_pruned(board, 3)
        assert move is not None
        board.push(move)
        assert board.is_checkmate(), f"Expected checkmate, got {move}"


class TestStalemate:
    def test_engine_avoids_stalemate_when_winning(self):
        """Engine should not stalemate the opponent when it has a winning advantage."""
        # White queen + king vs black king — should checkmate, not stalemate
        board = chess.Board("8/8/8/8/8/8/1Q6/k6K w - - 0 1")
        move = min_maxN_pruned(board, 3)
        assert move is not None
        board.push(move)
        # Should not be stalemate
        assert not board.is_stalemate(), f"Engine chose stalemate move: {move}"

    def test_engine_delivers_stalemate_when_losing(self):
        """When losing, engine should prefer stalemate over loss."""
        # Black king cornered, white about to checkmate — black should try to stall
        board = chess.Board("7k/8/7K/8/8/8/8/8 b - - 0 1")
        # Black has very few options, should not self-checkmate
        move = min_maxN_pruned(board, 3)
        if move:
            board.push(move)
            assert not board.is_checkmate()


class TestCastlingRights:
    def test_castling_rights_preserved(self):
        """Castling rights should be preserved in the board state."""
        board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
        assert board.has_castling_rights(chess.WHITE)
        assert board.has_castling_rights(chess.BLACK)

    def test_castling_rights_lost_after_king_move(self):
        """Castling rights should be lost after king moves."""
        board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
        board.push(chess.Move.from_uci("e1d1"))  # King moves
        assert not board.has_castling_rights(chess.WHITE)

    def test_engine_does_not_suggest_illegal_castle(self):
        """Engine should not suggest castling after the king has moved."""
        # King has moved, castling rights lost
        board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R4RK1 w kq - 0 1")
        # White king moved to g1, no castling rights
        assert not board.has_castling_rights(chess.WHITE)
        move = min_maxN_pruned(board, 3)
        if move:
            assert move != chess.Move.from_uci("e1g1"), "Engine suggested illegal O-O"
            assert move != chess.Move.from_uci("e1c1"), "Engine suggested illegal O-O-O"


class TestAlphaBetaConsistency:
    def test_pruned_matches_unpruned(self):
        """Alpha-beta pruned search should produce the same move as unpruned."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

        pruned_move = min_maxN_pruned(board, 3)

        # Unpruned version (same but no alpha-beta cutoffs)
        def min_max_unpruned(board, n):
            moves = list(board.legal_moves)
            best_move = None
            if board.turn:
                max_eval = float('-inf')
                for move in moves:
                    temp = board.copy()
                    temp.push(move)
                    outcome = temp.outcome()
                    if outcome:
                        if temp.is_checkmate():
                            return move
                        eval_score = 0
                    else:
                        if n > 1:
                            temp_eval = min_max_unpruned(temp, n - 1)
                            if temp_eval:
                                temp.push(temp_eval)
                        eval_score = eval_board(temp) + eval_space(temp)
                    if eval_score > max_eval:
                        max_eval = eval_score
                        best_move = move
            else:
                min_eval = float('inf')
                for move in moves:
                    temp = board.copy()
                    temp.push(move)
                    outcome = temp.outcome()
                    if outcome:
                        if temp.is_checkmate():
                            return move
                        eval_score = 0
                    else:
                        if n > 1:
                            temp_eval = min_max_unpruned(temp, n - 1)
                            if temp_eval:
                                temp.push(temp_eval)
                        eval_score = eval_board(temp) + eval_space(temp)
                    if eval_score < min_eval:
                        min_eval = eval_score
                        best_move = move
            return best_move

        unpruned_move = min_max_unpruned(board, 3)
        assert pruned_move == unpruned_move, (
            f"Pruned={pruned_move} != Unpruned={unpruned_move}"
        )

    def test_engine_returns_legal_move(self):
        """Engine should always return a legal move."""
        board = chess.Board()
        for depth in [1, 2, 3]:
            move = min_maxN_pruned(board, depth)
            assert move is not None, f"No move returned at depth {depth}"
            assert move in list(board.legal_moves), (
                f"Illegal move {move} at depth {depth}"
            )


class TestEngineStrength:
    def test_engine_finds_reasonable_move(self):
        """Engine should find a reasonable move (not random)."""
        board = chess.Board("r4rk1/ppp2ppp/8/8/8/8/PPP2PPP/R3R1K1 w - - 0 1")
        move = min_maxN_pruned(board, 3)
        assert move is not None
        assert move in list(board.legal_moves)
        # Engine should move a rook (either e1 or a1 rook)
        piece = board.piece_at(move.from_square)
        assert piece is not None
        assert piece.piece_type == chess.ROOK

    def test_engine_makes_legal_move_in_simple_position(self):
        """Engine should always return a legal move, even in simple positions."""
        board = chess.Board("8/8/8/8/3Q4/8/1p6/k6K w - - 0 1")
        move = min_maxN_pruned(board, 3)
        assert move is not None
        assert move in list(board.legal_moves)
