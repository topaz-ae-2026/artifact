function plural(word: string, n: int) -> string {
  if n == 1 {
    "{n} {word}"
  } else {
    "{n} {word}s"
  }
}

print(plural("dog", 2))
print(plural("row", 1))
print(plural("byte", 100))
print(plural("egg", 0))
print(plural("책", 5))
