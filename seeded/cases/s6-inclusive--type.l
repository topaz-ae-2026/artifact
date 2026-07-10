function sumTo(n: int) -> string {
    let mut total = 0
    for k in 1 .. n {
        total += k
    }
    return total
}
