function step(n: int) -> int {
    if n == 0 {
        return 0
    }
    return n + step(n - 1)
}
print("{step(100)}")
