function plural(word: string, n: int) -> string {
    if (n == 1) {
        return to_string(n) + " " + word;
    }
    return to_string(n) + " " + word + "s";
}
