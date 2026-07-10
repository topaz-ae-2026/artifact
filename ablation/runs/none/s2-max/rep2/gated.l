function maxOf(xs: Array<int>) -> int {
    let maximum: int = xs[0];
    for (let i: int = 1; i < xs.length; i = i + 1) {
        if (xs[i] > maximum) {
            maximum = xs[i];
        }
    }
    return maximum;
}

print("{maxOf([0, 0])}")
print("{maxOf([1, 2, 3, 4, 5])}")
print("{maxOf([9, 2, 9])}")
print("{maxOf([-100, -200])}")
print("{maxOf([7, 7, 7])}")
