function sumEvens(xs: Array<int>) -> string {
    let mut total = 0
    for x in xs {
        if x % 2 == 0 {
            total += x
        }
    }
    return total
}
