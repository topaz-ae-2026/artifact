function sumEvens(xs: Array<int>) -> int {
  reduce(filter(xs, x => x % 2 == 0), 0, (acc, x) => acc + x)
}

print("{sumEvens([2, 4, 6])}")
print("{sumEvens([0])}")
print("{sumEvens([1, 3, 5])}")
print("{sumEvens([10, 11, 12, 13, 14])}")
print("{sumEvens([8])}")
