function countAbove(xs: Array<int>, t: int) -> int {
    let mut n = 0
    for x in xs {
        if x > t {
            n += 1
        }
    }
    return n
}
