function sum(xs: Array<int>) -> int {
  reduce(xs, 0, (acc, x) => acc + x)
}

function maximum(xs: Array<int>) -> int {
  reduce(xs, xs[0], (acc, x) => if x > acc { x } else { acc })
}

function report(xs: Array<int>) -> string {
  "sum={sum(xs)} max={maximum(xs)}"
}
