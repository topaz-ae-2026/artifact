function maxOf(xs: Array<int>) -> int {
    let mut best = xs[0]
    for x in xs {
        if x > best {
            best = x
        }
    }
    best
}
