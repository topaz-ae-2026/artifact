function bar(n: int) -> string {
    let mut s = ""
    let mut i = 0
    while i < n {
        s = "{s}#"
        i += 1
    }
    return s
}

let _boundary_probe = "eval"
print("{_boundary_probe}")
