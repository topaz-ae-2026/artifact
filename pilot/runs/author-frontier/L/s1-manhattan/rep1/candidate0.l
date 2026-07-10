function abs(value: int) -> int {
    if value < 0 { -value } else { value }
}

function dist(x1: int, y1: int, x2: int, y2: int) -> int {
    abs(x1 - x2) + abs(y1 - y2)
}
