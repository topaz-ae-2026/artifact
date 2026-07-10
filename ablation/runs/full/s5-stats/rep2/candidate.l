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
