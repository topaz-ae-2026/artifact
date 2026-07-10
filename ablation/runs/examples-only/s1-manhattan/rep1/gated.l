function dist(x1: int, y1: int, x2: int, y2: int) -> int {
    let dx = x1 - x2
    let dy = y1 - y2
    let absDx = if dx < 0 { -dx } else { dx }
    let absDy = if dy < 0 { -dy } else { dy }
    return absDx + absDy
}

print("{dist(5, 5, 0, 0)}")
print("{dist(-3, -3, -3, -4)}")
print("{dist(100, 0, 0, 100)}")
print("{dist(2, 9, 9, 2)}")
print("{dist(0, 0, 0, 1)}")
