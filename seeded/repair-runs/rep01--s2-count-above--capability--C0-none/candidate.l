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
