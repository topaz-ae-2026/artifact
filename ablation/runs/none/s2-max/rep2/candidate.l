function maxOf(xs: Array<int>) -> int {
    let maximum: int = xs[0];
    for (let i: int = 1; i < xs.length; i = i + 1) {
        if (xs[i] > maximum) {
            maximum = xs[i];
        }
    }
    return maximum;
}
