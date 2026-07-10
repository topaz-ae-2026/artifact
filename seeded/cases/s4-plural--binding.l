function plural(word: string, n: int) -> string {
    if n == 1 {
        return "1 {zz_undef_name}"
    }
    return "{n} {word}s"
}
