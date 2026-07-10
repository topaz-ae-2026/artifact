function greet(name: string, hour: int) -> string {
  if hour < 12 {
    "Good morning, " + name
  } else if hour < 18 {
    "Good afternoon, " + name
  } else {
    "Good evening, " + name
  }
}
