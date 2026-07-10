function maxOf(xs: Array<int>) -> int {
    let mut maximum = xs[0]
    for x in xs {
        if x > maximum {
            maximum = x
        }
    }
    maximum
}

print("{maxOf([0, 0])}")
print("{maxOf([1, 2, 3, 4, 5])}")
print("{maxOf([9, 2, 9])}")
print("{maxOf([-100, -200])}")
print("{maxOf([7, 7, 7])}")
