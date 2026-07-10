function sumArray(xs: Array<int>) -> int {
  reduce(xs, 0, (acc, x) => acc + x)
}

function maxArray(xs: Array<int>) -> int {
  reduce(xs, xs[0], (acc, x) => if x > acc { x } else { acc })
}

function report(xs: Array<int>) -> string {
  "sum={sumArray(xs)} max={maxArray(xs)}"
}

print(report([0, 0, 0]))
print(report([10, 20, 30]))
print(report([7]))
print(report([2, 9, 4, 9]))
print(report([1, 1, 1, 1, 1]))
