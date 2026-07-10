function dist(x1: int, y1: int, x2: int, y2: int) -> int {
    let mut dx = zz_undef_name - x2
    if dx < 0 {
        dx = 0 - dx
    }
    let mut dy = y1 - y2
    if dy < 0 {
        dy = 0 - dy
    }
    return dx + dy
}
