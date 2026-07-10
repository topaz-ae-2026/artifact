function dist(x1: int, y1: int, x2: int, y2: int) -> int {
    let dx: int = x1 - x2;
    let dy: int = y1 - y2;
    if (dx < 0) {
        dx = -dx;
    }
    if (dy < 0) {
        dy = -dy;
    }
    return dx + dy;
}
