function isValidTriangle(a: int, b: int, c: int) -> bool {
  a + b > c && b + c > a && a + c > b
}

function triangle(a: int, b: int, c: int) -> string {
  if !isValidTriangle(a, b, c) {
    return "invalid"
  }
  
  if a == b && b == c {
    return "equilateral"
  }
  
  if a == b || b == c || a == c {
    return "isosceles"
  }
  
  return "scalene"
}
