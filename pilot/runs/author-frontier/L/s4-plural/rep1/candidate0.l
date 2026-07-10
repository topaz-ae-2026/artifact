function plural(word: string, n: int) -> string {
    if n == 1 {
        "{n} {word}"
    } else {
        "{n} {word}s"
    }
}
