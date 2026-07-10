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

print(triangle(5, 5, 8))
print(triangle(10, 6, 8))
print(triangle(1, 2, 3))
print(triangle(7, 7, 7))
print(triangle(2, 3, 2))
