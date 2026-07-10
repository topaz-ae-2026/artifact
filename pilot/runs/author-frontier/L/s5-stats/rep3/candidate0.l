function sum(xs: Array<int>) -> int {
    let mut total = 0
    for x in xs {
        total += x
    }
    total
}

function maximum(xs: Array<int>) -> int {
    let mut result = xs[0]
    for x in xs {
        if x > result {
            result = x
        }
    }
    result
}

function report(xs: Array<int>) -> string {
    "sum={sum(xs)} max={maximum(xs)}"
}
