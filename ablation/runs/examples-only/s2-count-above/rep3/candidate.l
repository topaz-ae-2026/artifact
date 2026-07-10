function countAbove(xs: Array<int>, t: int) -> int {
    let mut count = 0
    for x in xs {
        if x > t {
            count += 1
        }
    }
    return count
}
