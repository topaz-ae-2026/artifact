function sumValues(xs: Array<int>) -> int {
    let mut total = 0
    for x in xs {
        total += x
    }
    return total
}

function maxValue(xs: Array<int>) -> int {
    let mut maximum = xs[0]
    for x in xs {
        if x > maximum {
            maximum = x
        }
    }
    return maximum
}

function report(xs: Array<int>) -> string {
    return "sum={sumValues(xs)} max={maxValue(xs)}"
}
