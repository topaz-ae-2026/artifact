function bar(n: int) -> string {
    if n == 0 {
        return "";
    }
    return "#" + bar(n - 1);
}
