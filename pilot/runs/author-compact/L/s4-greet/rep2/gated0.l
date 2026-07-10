function greet(name: string, hour: int) -> string {
  let greeting = if hour < 12 {
    "Good morning"
  } else if hour < 18 {
    "Good afternoon"
  } else {
    "Good evening"
  }
  greeting + ", " + name
}

print(greet("Dee", 0))
print(greet("Ed", 11))
print(greet("Fi", 12))
print(greet("Gil", 17))
print(greet("한나", 23))
