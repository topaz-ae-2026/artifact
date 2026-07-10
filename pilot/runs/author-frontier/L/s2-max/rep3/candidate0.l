function maxOf(xs: Array<int>) -> int {
    let mut largest = xs[0]
    let mut i = 1
    while i < xs.length {
        if xs[i] > largest {
            largest = xs[i]
        }
        i += 1
    }
    largest
}
