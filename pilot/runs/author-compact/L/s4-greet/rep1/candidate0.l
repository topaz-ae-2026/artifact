function greet(name: string, hour: int) -> string {
  let greeting = if hour < 12 {
    "Good morning"
  } else if hour < 18 {
    "Good afternoon"
  } else {
    "Good evening"
  }
  greeting + ", " + name
}
