function dot(xs: Array<int>, ys: Array<int>) -> int {
    let total: int = 0;
    let i: int = 0;
    while (i < xs.length) {
        total = total + xs[i] * ys[i];
        i = i + 1;
    }
    return total;
}
