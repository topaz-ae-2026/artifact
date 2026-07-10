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
