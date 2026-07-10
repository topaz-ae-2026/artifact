function dot(xs: Array<int>, ys: Array<int>) -> int {
    let result: int = 0;
    for (let i: int = 0; i < xs.length; i = i + 1) {
        result = result + xs[i] * ys[i];
    }
    return result;
}

print("{dot([1, 1, 1], [2, 3, 4])}")
print("{dot([0, 9], [7, 0])}")
print("{dot([2, 3], [4, 5])}")
print("{dot([-1, 2], [3, 4])}")
print("{dot([10], [10])}")
