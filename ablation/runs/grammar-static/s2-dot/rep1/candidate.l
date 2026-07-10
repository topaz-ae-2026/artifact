function dot(xs: Array<int>, ys: Array<int>) -> int {
    let mut total: int = 0
    for i in 0..<xs.length {
        total += xs[i] * ys[i]
    }
    total
}
