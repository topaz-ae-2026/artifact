function sumTo(n: int) -> int {
    let mut total = 0
    for k in 1 ..< n + 1 {
        total += k
    }
    return total
}
