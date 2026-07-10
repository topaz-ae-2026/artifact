function sumEvens(xs: Array<int>) -> int {
    let mut sum = 0
    for x in xs {
        if x % 2 == 0 {
            sum += x
        }
    }
    sum
}
