function clamp(n: int, lo: int, hi: int) -> int {
    if n < lo {
        return lo
    }
    if n > hi {
        return hi
    }
    return n
}
print("{clamp(15, 0, 10)} {clamp(-3, 0, 10)} {clamp(7, 0, 10)}")
