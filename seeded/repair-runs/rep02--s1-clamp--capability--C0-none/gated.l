function clamp(n: int, lo: int, hi: int) -> int {
    if n < lo {
        return lo
    }
    if n > hi {
        return hi
    }
    return n
}

let _boundary_probe = "eval"
print("{_boundary_probe}")

print("{clamp(0, 0, 10)}")
print("{clamp(10, 0, 10)}")
print("{clamp(7, 7, 7)}")
print("{clamp(-100, -50, 50)}")
print("{clamp(11, 0, 10)}")
