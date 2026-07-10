function countAbove(xs: Array<int>, t: int) -> string {
    let mut n = 0
    for x in xs {
        if x > t {
            n += 1
        }
    }
    return n
}
