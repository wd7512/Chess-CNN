import chess


def labels_from_fen(fen):
    fen_placement = fen.split(" ")[0]
    labels = []
    for char in fen_placement:
        if char.isdigit():
            labels.extend(['-'] * int(char))
        elif char == '/':
            continue
        else:
            labels.append(char)
    return labels


def _fen_idx(chess_sq):
    return (7 - chess_sq // 8) * 8 + chess_sq % 8


def verify_partial_diff(prev_fen, new_fen, move_uci):
    if not prev_fen or not new_fen:
        return True
    prev_labels = labels_from_fen(prev_fen)
    new_labels = labels_from_fen(new_fen)
    source_idx = _fen_idx(chess.parse_square(move_uci[:2]))
    dest_idx = _fen_idx(chess.parse_square(move_uci[2:4]))
    source_changed = prev_labels[source_idx] != new_labels[source_idx]
    dest_changed = prev_labels[dest_idx] != new_labels[dest_idx]
    return source_changed or dest_changed


class GameState:
    def __init__(self):
        self.last_fen = None
        self.move_count = 0
        self.fens = []

    def update(self, fen):
        self.last_fen = fen
        self.fens.append(fen)

    def verify_move(self, prev_fen, new_fen, move_uci):
        if not prev_fen or not new_fen:
            return True
        return verify_partial_diff(prev_fen, new_fen, move_uci)
