function plural(word: string, n: int) -> string {
    if (n == 1) {
        return n + " " + word;
    }
    return n + " " + word + "s";
}
