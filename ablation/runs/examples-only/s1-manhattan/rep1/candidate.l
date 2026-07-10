function dist(x1: int, y1: int, x2: int, y2: int) -> int {
    let dx = x1 - x2
    let dy = y1 - y2
    let absDx = if dx < 0 { -dx } else { dx }
    let absDy = if dy < 0 { -dy } else { dy }
    return absDx + absDy
}
