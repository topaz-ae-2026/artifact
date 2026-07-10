function maxOf(xs: Array<int>) -> int {
    let mut largest = xs[0]
    for x in xs {
        if x > largest {
            largest = x
        }
    }
    return largest
}
