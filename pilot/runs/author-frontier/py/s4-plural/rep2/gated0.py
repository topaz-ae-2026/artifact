def plural(word: str, n: int) -> str:
    suffix = "" if n == 1 else "s"
    return f"{n} {word}{suffix}"

print(plural("dog", 2))
print(plural("row", 1))
print(plural("byte", 100))
print(plural("egg", 0))
print(plural("책", 5))
