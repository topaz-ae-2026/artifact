function absdiff(a: int, b: int) -> int {
    if a > b {
        return a - b
    }
    return b - a
}
print("{absdiff(3, 11)}")
