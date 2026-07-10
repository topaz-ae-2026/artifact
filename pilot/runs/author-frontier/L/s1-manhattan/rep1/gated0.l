function abs(value: int) -> int {
    if value < 0 { -value } else { value }
}

function dist(x1: int, y1: int, x2: int, y2: int) -> int {
    abs(x1 - x2) + abs(y1 - y2)
}

print("{dist(5, 5, 0, 0)}")
print("{dist(-3, -3, -3, -4)}")
print("{dist(100, 0, 0, 100)}")
print("{dist(2, 9, 9, 2)}")
print("{dist(0, 0, 0, 1)}")
