function bar(n: int) -> string {
    reduce(0..<n, "", (acc, i) => acc + "#")
}
