function dot(xs: Array<int>, ys: Array<int>) -> int {
    let mut i = 0
    let mut total = 0
    while i < xs.length {
        total += xs[i] * ys[i]
        i += 1
    }
    total
}

print("{dot([1, 1, 1], [2, 3, 4])}")
print("{dot([0, 9], [7, 0])}")
print("{dot([2, 3], [4, 5])}")
print("{dot([-1, 2], [3, 4])}")
print("{dot([10], [10])}")
