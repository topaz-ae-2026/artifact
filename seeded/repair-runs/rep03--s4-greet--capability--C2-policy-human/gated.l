function greet(name: string, hour: int) -> string {
    if hour < 12 {
        return "Good morning, {name}"
    }
    if hour < 18 {
        return "Good afternoon, {name}"
    }
    return "Good evening, {name}"
}

print(greet("Dee", 0))
print(greet("Ed", 11))
print(greet("Fi", 12))
print(greet("Gil", 17))
print(greet("한나", 23))
