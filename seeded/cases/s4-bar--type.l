function bar(n: int) -> int {
    let mut s = ""
    let mut i = 0
    while i < n {
        s = "{s}#"
        i += 1
    }
    return s
}
