def dist(x1: int, y1: int, x2: int, y2: int) -> int:
    dx = x1 - x2
    if dx < 0:
        dx = -dx
    dy = y1 - y2
    if dy < 0:
        dy = -dy
    return dx + dy
