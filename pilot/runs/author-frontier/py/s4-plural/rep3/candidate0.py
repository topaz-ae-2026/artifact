def plural(word: str, n: int) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"
