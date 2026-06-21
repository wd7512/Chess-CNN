import chess


def labels_to_fen(labels):
    if len(labels) != 64:
        raise ValueError(f"Expected 64 labels, got {len(labels)}")
    board = chess.Board(None)
    for i, label in enumerate(labels):
        if label != '-':
            if label not in 'KkQqRrBbNnPp':
                raise ValueError(f"Invalid piece symbol: '{label}'")
            file_idx = i % 8
            rank_idx = 7 - i // 8
            square = chess.square(file_idx, rank_idx)
            board.set_piece_at(square, chess.Piece.from_symbol(label))
    return board.fen().split(" ")[0]


def fen_to_labels(fen):
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
