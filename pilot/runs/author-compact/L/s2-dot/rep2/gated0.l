function dot(xs: Array<int>, ys: Array<int>) -> int {
  let mut result = 0
  for i in 0..<xs.length {
    result += xs[i] * ys[i]
  }
  result
}

print("{dot([1, 1, 1], [2, 3, 4])}")
print("{dot([0, 9], [7, 0])}")
print("{dot([2, 3], [4, 5])}")
print("{dot([-1, 2], [3, 4])}")
print("{dot([10], [10])}")
