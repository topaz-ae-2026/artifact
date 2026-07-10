function dot(xs: Array<int>, ys: Array<int>) -> int {
    let mut total = 0
    let mut i = 0
    for x in xs {
        total += x * ys[i]
        i += 1
    }
    return total
}

print("{dot([1, 1, 1], [2, 3, 4])}")
print("{dot([0, 9], [7, 0])}")
print("{dot([2, 3], [4, 5])}")
print("{dot([-1, 2], [3, 4])}")
print("{dot([10], [10])}")
