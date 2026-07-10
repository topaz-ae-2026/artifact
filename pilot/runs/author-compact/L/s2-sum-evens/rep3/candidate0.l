function sumEvens(xs: Array<int>) -> int {
  reduce(xs, 0, (sum, x) => if x % 2 == 0 { sum + x } else { sum })
}
