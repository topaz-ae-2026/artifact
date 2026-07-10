def is_valid(a: int, b: int, c: int) -> str:
    if a + b > c and b + c > a and a + c > b:
        return "yes"
    return "no"


def triangle(a: int, b: int, c: int) -> str:
    if is_valid(a, b, c) == "no":
        return "invalid"
    if a == b and b == c:
        return "equilateral"
    if a == b or b == c or a == c:
        return "isosceles"
    return "scalene"
