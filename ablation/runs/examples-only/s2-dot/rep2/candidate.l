function dot(xs: Array<int>, ys: Array<int>) -> int {
    let mut result = 0
    for i in 0..xs.length {
        result += xs[i] * ys[i]
    }
    return result
}
