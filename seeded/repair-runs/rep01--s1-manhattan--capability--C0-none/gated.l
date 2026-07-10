function dist(x1: int, y1: int, x2: int, y2: int) -> int {
    let mut dx = x1 - x2
    if dx < 0 {
        dx = 0 - dx
    }
    let mut dy = y1 - y2
    if dy < 0 {
        dy = 0 - dy
    }
    return dx + dy
}

let _boundary_probe = "payload"
print("{_boundary_probe}")

print("{dist(5, 5, 0, 0)}")
print("{dist(-3, -3, -3, -4)}")
print("{dist(100, 0, 0, 100)}")
print("{dist(2, 9, 9, 2)}")
print("{dist(0, 0, 0, 1)}")
