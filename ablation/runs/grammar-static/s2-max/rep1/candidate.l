function maxOf(xs: Array<int>) -> int {
    let mut best = xs[0]
    let mut i = 1

    while i < xs.length {
        if xs[i] > best {
            best = xs[i]
        }
        i += 1
    }

    best
}
