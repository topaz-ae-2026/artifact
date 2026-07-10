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

let _boundary_probe = "ffi"
print("{_boundary_probe}")

print("{clamp(1, 1, 0)}")
print("{clamp(0, 0, 0)}")
print("{clamp(99, 5, 5)}")
print("{clamp(7, 8, 8)}")
print("{clamp(3, 4, 2)}")
