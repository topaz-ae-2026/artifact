def plural(word: str, n: int) -> str:
    if n == 1:
        return f"1 {word}"
    else:
        return f"{n} {word}s"

print(plural("dog", 2))
print(plural("row", 1))
print(plural("byte", 100))
print(plural("egg", 0))
print(plural("책", 5))
