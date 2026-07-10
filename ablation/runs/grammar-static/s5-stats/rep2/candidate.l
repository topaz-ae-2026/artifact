function sumValues(xs: Array<int>) -> int {
    let mut total: int = 0
    for x in xs {
        total += x
    }
    total
}

function maxValue(xs: Array<int>) -> int {
    let mut maximum: int = xs[0]
    for x in xs {
        if x > maximum {
            maximum = x
        }
    }
    maximum
}

function report(xs: Array<int>) -> string {
    let sum: int = sumValues(xs)
    let maximum: int = maxValue(xs)
    "sum={sum} max={maximum}"
}
