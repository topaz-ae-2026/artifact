function dot(xs: Array<int>, ys: Array<int>) -> int {
    let mut total = 0
    let mut i = 0
    for x in xs {
        total += x * ys[i]
        i += 1
    }
    return total
}
