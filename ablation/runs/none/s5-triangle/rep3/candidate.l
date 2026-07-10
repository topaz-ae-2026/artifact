function isValidTriangle(a: int, b: int, c: int) -> bool {
    return a + b > c && a + c > b && b + c > a;
}

function triangle(a: int, b: int, c: int) -> string {
    if (!isValidTriangle(a, b, c)) {
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
