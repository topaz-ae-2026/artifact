function grade(score: int) -> string {
  if score >= 90 {
    "A"
  } else if score >= 80 {
    "B"
  } else if score >= 70 {
    "C"
  } else if score >= 60 {
    "D"
  } else {
    "F"
  }
}

print(grade(90))
print(grade(89))
print(grade(60))
print(grade(59))
print(grade(100))
