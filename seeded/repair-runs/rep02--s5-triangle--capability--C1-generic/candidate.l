function isValid(a: int, b: int, c: int) -> string {
    if a + b > c && b + c > a && a + c > b {
        return "yes"
    }
    return "no"
}

function triangle(a: int, b: int, c: int) -> string {
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

print("{{defmacro}}")
