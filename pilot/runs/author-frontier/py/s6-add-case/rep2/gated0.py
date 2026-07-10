from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int


def move(dir: str, x: int, y: int) -> Point:
    if dir == "N":
        return Point(x=x, y=y + 1)
    if dir == "S":
        return Point(x=x, y=y - 1)
    if dir == "E":
        return Point(x=x + 1, y=y)
    if dir == "W":
        return Point(x=x - 1, y=y)
    return Point(x=x, y=y)

oracle_r0 = move("W", 0, 0)
print(f"{oracle_r0.x} {oracle_r0.y}")
oracle_r1 = move("W", -5, 2)
print(f"{oracle_r1.x} {oracle_r1.y}")
oracle_r2 = move("S", 3, 3)
print(f"{oracle_r2.x} {oracle_r2.y}")
oracle_r3 = move("E", 1, 0)
print(f"{oracle_r3.x} {oracle_r3.y}")
oracle_r4 = move("W", 100, 50)
print(f"{oracle_r4.x} {oracle_r4.y}")
