function sumValues(xs: Array<int>) -> int {
    let mut total = 0
    let mut i = 0
    while i < xs.length {
        total += xs[i]
        i += 1
    }
    total
}

function maxValue(xs: Array<int>) -> int {
    let mut maximum = xs[0]
    let mut i = 1
    while i < xs.length {
        if xs[i] > maximum {
            maximum = xs[i]
        }
        i += 1
    }
    maximum
}

function report(xs: Array<int>) -> string {
    let total = sumValues(xs)
    let maximum = maxValue(xs)
    "sum={total} max={maximum}"
}

print(report([0, 0, 0]))
print(report([10, 20, 30]))
print(report([7]))
print(report([2, 9, 4, 9]))
print(report([1, 1, 1, 1, 1]))
