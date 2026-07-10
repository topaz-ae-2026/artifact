function isValidTriangle(a: int, b: int, c: int) -> bool {
    a > 0 && b > 0 && c > 0 &&
    a > c - b && b > c - a && c > b - a
}

function triangle(a: int, b: int, c: int) -> string {
    if !isValidTriangle(a, b, c) {
        "invalid"
    } else if a == b && b == c {
        "equilateral"
    } else if a == b || b == c || a == c {
        "isosceles"
    } else {
        "scalene"
    }
}
