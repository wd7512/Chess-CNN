def uci_to_pixels(uci, board_rect, is_white):
    x = board_rect['x']
    y = board_rect['y']
    w = board_rect.get('w', board_rect.get('width', 0))
    h = board_rect.get('h', board_rect.get('height', 0))
    square_size = ((w + h) // 2) // 8

    source = uci[:2]
    dest = uci[2:4]

    if is_white:
        sx = x + (ord(source[0]) - 97 + 0.5) * square_size
        sy = y + (8 - int(source[1]) + 0.5) * square_size
        ex = x + (ord(dest[0]) - 97 + 0.5) * square_size
        ey = y + (8 - int(dest[1]) + 0.5) * square_size
    else:
        sx = x + w - (ord(source[0]) - 97 + 0.5) * square_size
        sy = y + h - (int(source[1]) - 1 + 0.5) * square_size
        ex = x + w - (ord(dest[0]) - 97 + 0.5) * square_size
        ey = y + h - (int(dest[1]) - 1 + 0.5) * square_size

    return (sx, sy, ex, ey)
