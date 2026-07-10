function bar(n: int) -> string {
    if (n == 0) {
        return "";
    }
    return "#" + bar(n - 1);
}

print(bar(5))
print(bar(7))
print(bar(2))
print(bar(10))
print(bar(4))
