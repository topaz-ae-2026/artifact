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

print(report([0, 0, 0]))
print(report([10, 20, 30]))
print(report([7]))
print(report([2, 9, 4, 9]))
print(report([1, 1, 1, 1, 1]))
