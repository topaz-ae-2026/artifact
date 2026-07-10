function sumInts(xs: Array<int>) -> int {
    let mut total = 0
    for x in xs {
        total += x
    }
    total
}

function maxInt(xs: Array<int>) -> int {
    let mut maximum = xs[0]
    for x in xs {
        if x > maximum {
            maximum = x
        }
    }
    maximum
}

function report(xs: Array<int>) -> string {
    let sum = sumInts(xs)
    let maximum = maxInt(xs)
    "sum={sum} max={maximum}"
}
