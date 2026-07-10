function dot(xs: Array<int>, ys: Array<int>) -> string {
    let mut total = 0
    for k in 0 ..< xs.length {
        total += xs[k] * ys[k]
    }
    return total
}
