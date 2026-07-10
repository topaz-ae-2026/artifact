function clamp(n: int, lo: int, hi: int) -> string {
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
