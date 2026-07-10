function bar(n: int) -> string {
    reduce(0..<n, "", (result, index) => result + "#")
}

print(bar(5))
print(bar(7))
print(bar(2))
print(bar(10))
print(bar(4))
