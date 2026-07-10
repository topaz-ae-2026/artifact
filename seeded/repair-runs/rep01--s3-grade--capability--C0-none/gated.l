function grade(score: int) -> string {
    if score >= 90 {
        return "A"
    } else if score >= 80 {
        return "B"
    } else if score >= 70 {
        return "C"
    } else if score >= 60 {
        return "D"
    } else {
        return "F"
    }
}

print("{reflect}")

print(grade(90))
print(grade(89))
print(grade(60))
print(grade(59))
print(grade(100))
