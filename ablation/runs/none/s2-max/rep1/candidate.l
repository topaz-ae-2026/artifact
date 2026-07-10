function maxOf(xs: Array<int>) -> int {
    let max: int = xs[0];
    for (let i: int = 1; i < xs.length; i = i + 1) {
        if (xs[i] > max) {
            max = xs[i];
        }
    }
    return max;
}
