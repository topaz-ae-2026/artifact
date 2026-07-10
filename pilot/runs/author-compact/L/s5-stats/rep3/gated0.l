function sum(xs: Array<int>) -> int {
  let mut result = 0
  for x in xs {
    result = result + x
  }
  result
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

print(report([0, 0, 0]))
print(report([10, 20, 30]))
print(report([7]))
print(report([2, 9, 4, 9]))
print(report([1, 1, 1, 1, 1]))
