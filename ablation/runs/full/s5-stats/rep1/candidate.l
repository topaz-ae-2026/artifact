function sum(xs: Array<int>) -> int {
    let mut total = 0
    for x in xs {
        total += x
    }
    total
}

function maximum(xs: Array<int>) -> int {
    let mut best = xs[0]
    for x in xs {
        if x > best {
            best = x
        }
    }
    best
}

function report(xs: Array<int>) -> string {
    "sum={sum(xs)} max={maximum(xs)}"
}
