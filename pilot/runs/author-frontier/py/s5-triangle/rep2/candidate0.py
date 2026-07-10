def _is_valid_triangle(a: int, b: int, c: int) -> bool:
    return a > 0 and b > 0 and c > 0 and a + b > c and a + c > b and b + c > a


def triangle(a: int, b: int, c: int) -> str:
    if not _is_valid_triangle(a, b, c):
        return "invalid"
    if a == b == c:
        return "equilateral"
    if a == b or a == c or b == c:
        return "isosceles"
    return "scalene"
