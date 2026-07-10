function dot(xs: Array<int>, ys: Array<int>) -> int {
    let result: int = 0;
    for (let i: int = 0; i < xs.length; i = i + 1) {
        result = result + xs[i] * ys[i];
    }
    return result;
}
