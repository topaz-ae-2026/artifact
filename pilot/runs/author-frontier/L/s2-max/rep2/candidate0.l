function maxOf(xs: Array<int>) -> int {
    let mut maximum = xs[0]
    for x in xs {
        if x > maximum {
            maximum = x
        }
    }
    maximum
}
