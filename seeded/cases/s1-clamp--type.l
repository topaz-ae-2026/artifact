function clamp(n: int, lo: int, hi: int) -> string {
    if n < lo {
        return lo
    }
    if n > hi {
        return hi
    }
    return n
}
