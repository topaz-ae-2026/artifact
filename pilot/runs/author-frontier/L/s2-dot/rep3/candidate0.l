function dot(xs: Array<int>, ys: Array<int>) -> int {
    let mut total = 0
    let mut i = 0
    while i < xs.length {
        total += xs[i] * ys[i]
        i += 1
    }
    total
}
