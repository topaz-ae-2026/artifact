function bar(n: int) -> string {
    let mut result = ""
    let mut i = 0
    while i < n {
        result += "#"
        i += 1
    }
    result
}

print(bar(5))
print(bar(7))
print(bar(2))
print(bar(10))
print(bar(4))
