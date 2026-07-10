function sum(xs: Array<int>) -> int {
    let total: int = 0;
    for (x: int in xs) {
        total = total + x;
    }
    return total;
}

function maximum(xs: Array<int>) -> int {
    let result: int = xs[0];
    for (x: int in xs) {
        if (x > result) {
            result = x;
        }
    }
    return result;
}

function report(xs: Array<int>) -> string {
    return "sum=" + toString(sum(xs)) + " max=" + toString(maximum(xs));
}
