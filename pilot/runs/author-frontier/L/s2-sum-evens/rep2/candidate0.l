function sumEvens(xs: Array<int>) -> int {
    reduce(
        filter(xs, x => x % 2 == 0),
        0,
        (sum, x) => sum + x,
    )
}
