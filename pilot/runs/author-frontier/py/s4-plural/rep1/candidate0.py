def plural(word: str, n: int) -> str:
    suffix = "" if n == 1 else "s"
    return f"{n} {word}{suffix}"
