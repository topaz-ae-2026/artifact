function dot(xs: Array<int>, ys: Array<int>) -> int {
    let sum: int = 0;
    let i: int = 0;
    while (i < xs.length) {
        sum = sum + xs[i] * ys[i];
        i = i + 1;
    }
    return sum;
}
