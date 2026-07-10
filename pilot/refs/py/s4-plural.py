def plural(word: str, n: int) -> str:
    if n == 1:
        return f"1 {word}"
    return f"{n} {word}s"
