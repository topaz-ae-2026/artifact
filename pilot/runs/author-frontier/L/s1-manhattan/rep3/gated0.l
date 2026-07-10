function dist(x1: int, y1: int, x2: int, y2: int) -> int {
    let dx = if x1 >= x2 { x1 - x2 } else { x2 - x1 }
    let dy = if y1 >= y2 { y1 - y2 } else { y2 - y1 }
    dx + dy
}

print("{dist(5, 5, 0, 0)}")
print("{dist(-3, -3, -3, -4)}")
print("{dist(100, 0, 0, 100)}")
print("{dist(2, 9, 9, 2)}")
print("{dist(0, 0, 0, 1)}")
