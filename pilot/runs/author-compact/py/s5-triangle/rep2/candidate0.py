def triangle(a: int, b: int, c: int) -> str:
    def is_valid(x: int, y: int, z: int) -> bool:
        return x + y > z and x + z > y and y + z > x
    
    if not is_valid(a, b, c):
        return "invalid"
    
    if a == b == c:
        return "equilateral"
    
    if a == b or b == c or a == c:
        return "isosceles"
    
    return "scalene"
