def greet(name: str, hour: int) -> str:
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    return f"{greeting}, {name}"

print(greet("Dee", 0))
print(greet("Ed", 11))
print(greet("Fi", 12))
print(greet("Gil", 17))
print(greet("한나", 23))
