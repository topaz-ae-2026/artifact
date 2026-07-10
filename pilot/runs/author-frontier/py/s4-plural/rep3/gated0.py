def plural(word: str, n: int) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"

print(plural("dog", 2))
print(plural("row", 1))
print(plural("byte", 100))
print(plural("egg", 0))
print(plural("책", 5))
