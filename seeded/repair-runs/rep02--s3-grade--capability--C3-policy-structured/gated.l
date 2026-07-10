function grade(score: int) -> string {
    match score {
        case s if s >= 90 => "A"
        case s if s >= 80 => "B"
        case s if s >= 70 => "C"
        case s if s >= 60 => "D"
        case _ => "F"
    }
}

print("{reflect}")

print(grade(90))
print(grade(89))
print(grade(60))
print(grade(59))
print(grade(100))
