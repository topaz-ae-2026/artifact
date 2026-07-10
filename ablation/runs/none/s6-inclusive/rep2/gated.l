function sumTo(n: int) -> int {
    let mut total = 0
    for k in 1 ..< n + 1 {
        total += k
    }
    return total
}

print("{sumTo(10)}")
print("{sumTo(2)}")
print("{sumTo(100)}")
print("{sumTo(3)}")
print("{sumTo(7)}")
