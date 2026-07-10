function sumArray(xs: Array<int>) -> int {
    var total: int = 0;
    var i: int = 0;
    while (i < xs.length) {
        total = total + xs[i];
        i = i + 1;
    }
    return total;
}

function maxArray(xs: Array<int>) -> int {
    var maximum: int = xs[0];
    var i: int = 1;
    while (i < xs.length) {
        if (xs[i] > maximum) {
            maximum = xs[i];
        }
        i = i + 1;
    }
    return maximum;
}

function report(xs: Array<int>) -> string {
    return "sum=" + toString(sumArray(xs)) + " max=" + toString(maxArray(xs));
}

print(report([0, 0, 0]))
print(report([10, 20, 30]))
print(report([7]))
print(report([2, 9, 4, 9]))
print(report([1, 1, 1, 1, 1]))
