function bar(n: int) -> string {
  reduce(0..<n, "", (acc, _x) => acc + "#")
}
