function sumValues(xs: Array<int>) -> int {
    let mut total = 0
    for x in xs {
        total += x
    }
    total
}

function maxValue(xs: Array<int>) -> int {
    let mut maximum = xs[0]
    for x in xs {
        if x > maximum {
            maximum = x
        }
    }
    maximum
}

function report(xs: Array<int>) -> string {
    "sum={sumValues(xs)} max={maxValue(xs)}"
}

print(report([0, 0, 0]))
print(report([10, 20, 30]))
print(report([7]))
print(report([2, 9, 4, 9]))
print(report([1, 1, 1, 1, 1]))
