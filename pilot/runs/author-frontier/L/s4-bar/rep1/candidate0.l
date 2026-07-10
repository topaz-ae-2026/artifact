function bar(n: int) -> string {
    reduce(0..<n, "", (result, _) => result + "#")
}
