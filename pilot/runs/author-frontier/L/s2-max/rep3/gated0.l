function maxOf(xs: Array<int>) -> int {
    let mut largest = xs[0]
    let mut i = 1
    while i < xs.length {
        if xs[i] > largest {
            largest = xs[i]
        }
        i += 1
    }
    largest
}

print("{maxOf([0, 0])}")
print("{maxOf([1, 2, 3, 4, 5])}")
print("{maxOf([9, 2, 9])}")
print("{maxOf([-100, -200])}")
print("{maxOf([7, 7, 7])}")
