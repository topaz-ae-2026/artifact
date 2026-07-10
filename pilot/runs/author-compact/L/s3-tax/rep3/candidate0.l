function tax(income: int) -> int {
  if income <= 1000 {
    0
  } else if income <= 5000 {
    income - 1000
  } else {
    4000 + 3 * (income - 5000)
  }
}
