function plural(word: string, n: int) -> int {
    if n == 1 {
        return "1 {word}"
    }
    return "{n} {word}s"
}
