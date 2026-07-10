function greet(name: string, hour: int) -> string {
  if hour < 12 {
    "Good morning, " + name
  } else if hour < 18 {
    "Good afternoon, " + name
  } else {
    "Good evening, " + name
  }
}

print(greet("Dee", 0))
print(greet("Ed", 11))
print(greet("Fi", 12))
print(greet("Gil", 17))
print(greet("한나", 23))
