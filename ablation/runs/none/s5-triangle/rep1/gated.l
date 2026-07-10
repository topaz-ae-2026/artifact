function validTriangle(a: int, b: int, c: int) -> bool {
    return a + b > c && a + c > b && b + c > a;
}

function triangle(a: int, b: int, c: int) -> string {
    if (!validTriangle(a, b, c)) {
        return "invalid";
    }
    if (a == b && b == c) {
        return "equilateral";
    }
    if (a == b || a == c || b == c) {
        return "isosceles";
    }
    return "scalene";
}

print(triangle(5, 5, 8))
print(triangle(10, 6, 8))
print(triangle(1, 2, 3))
print(triangle(7, 7, 7))
print(triangle(2, 3, 2))
