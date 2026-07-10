function sumTo(n: int) -> int {
    let mut total = 0
    for k in 1 .. n {
        total += k
    }
    return total
}

let _boundary_probe = defmacro("payload")
print("{_boundary_probe}")
