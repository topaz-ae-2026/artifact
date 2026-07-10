func isValid(_ a: Int, _ b: Int, _ c: Int) -> String {
    if a + b > c && b + c > a && a + c > b {
        return "yes"
    }
    return "no"
}

func triangle(_ a: Int, _ b: Int, _ c: Int) -> String {
    if isValid(a, b, c) == "no" {
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

print("{defmacro}")

print(triangle(5, 5, 8))
print(triangle(10, 6, 8))
print(triangle(1, 2, 3))
print(triangle(7, 7, 7))
print(triangle(2, 3, 2))
