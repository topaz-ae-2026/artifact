function isValidTriangle(a: int, b: int, c: int) -> bool {
    a + b > c && a + c > b && b + c > a
}

function triangle(a: int, b: int, c: int) -> string {
    if !isValidTriangle(a, b, c) {
        "invalid"
    } else if a == b && b == c {
        "equilateral"
    } else if a == b || a == c || b == c {
        "isosceles"
    } else {
        "scalene"
    }
}
