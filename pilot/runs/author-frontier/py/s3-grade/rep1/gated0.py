def grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"

print(grade(90))
print(grade(89))
print(grade(60))
print(grade(59))
print(grade(100))
