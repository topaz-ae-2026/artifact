function leapLabel(y: int) -> string {
  if y % 400 == 0 {
    "leap"
  } else if y % 100 == 0 {
    "common"
  } else if y % 4 == 0 {
    "leap"
  } else {
    "common"
  }
}

print(leapLabel(2023))
print(leapLabel(1600))
print(leapLabel(2100))
print(leapLabel(4))
print(leapLabel(1))
