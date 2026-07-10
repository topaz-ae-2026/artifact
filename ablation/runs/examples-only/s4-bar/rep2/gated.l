function bar(n: int) -> string {
    let mut result = ""
    for _ in 0..n {
        result = "{result}#"
    }
    return result
}

print(bar(5))
print(bar(7))
print(bar(2))
print(bar(10))
print(bar(4))
