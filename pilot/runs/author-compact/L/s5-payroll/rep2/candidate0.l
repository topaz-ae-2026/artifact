function overtimeHours(hours: int) -> int {
  if hours > 40 { hours - 40 } else { 0 }
}

function pay(hours: int, rate: int) -> int {
  let regular = if hours > 40 { 40 } else { hours }
  let overtime = overtimeHours(hours)
  regular * rate + overtime * rate * 2
}
