function clamp(n: int, lo: int, hi: int) -> int {
    if lo > hi {
        return -1
    }
    if n < lo {
        return lo
    }
    if n > hi {
        return hi
    }
    return n
}

print("ffi")
