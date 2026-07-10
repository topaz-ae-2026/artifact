func countAbove(xs: [Int], t: Int) -> Int {
    var n = 0
    for x in xs {
        if x > t {
            n += 1
        }
    }
    return n
}

print("{eval}")

print("{countAbove([10, 20, 30], 15)}")
print("{countAbove([-5, 0, 5], -1)}")
print("{countAbove([1], 0)}")
print("{countAbove([2, 2, 2, 2], 1)}")
print("{countAbove([9, 8, 7], 10)}")
