function bar(n: int) -> string {
    if n == 0 {
        ""
    } else {
        "#" + bar(n - 1)
    }
}
