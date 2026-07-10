function sumOf(xs: Array<int>) -> int {
    let mut total = 0
    for x in xs {
        total += x
    }
    return total
}
function maxOf(xs: Array<int>) -> int {
    let mut best = xs[0]
    for k in 1 ..< xs.length {
        if xs[k] >= best {
            best = xs[k]
        }
    }
    return best
}
function report(xs: Array<int>) -> string {
    return "sum={sumOf(xs)} max={maxOf(xs)}"
}
