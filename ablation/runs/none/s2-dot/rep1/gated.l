function dot(xs: Array<int>, ys: Array<int>) -> int {
    let sum: int = 0;
    let i: int = 0;
    while (i < xs.length) {
        sum = sum + xs[i] * ys[i];
        i = i + 1;
    }
    return sum;
}

print("{dot([1, 1, 1], [2, 3, 4])}")
print("{dot([0, 9], [7, 0])}")
print("{dot([2, 3], [4, 5])}")
print("{dot([-1, 2], [3, 4])}")
print("{dot([10], [10])}")
