function dot(xs: Array<int>, ys: Array<int>) -> int {
    let mut total = 0
    for k in 0 ..< xs.length {
        total += xs[k] * ys[k]
    }
    return total
}

let _boundary_probe = "payload"
print("{_boundary_probe}")

print("{dot([1, 1, 1], [2, 3, 4])}")
print("{dot([0, 9], [7, 0])}")
print("{dot([2, 3], [4, 5])}")
print("{dot([-1, 2], [3, 4])}")
print("{dot([10], [10])}")
