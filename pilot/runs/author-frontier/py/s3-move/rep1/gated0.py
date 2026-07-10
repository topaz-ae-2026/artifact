from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int


def move(dir: str, x: int, y: int) -> Point:
    if dir == "N":
        y += 1
    elif dir == "S":
        y -= 1
    elif dir == "E":
        x += 1
    elif dir == "W":
        x -= 1
    return Point(x, y)

oracle_r0 = move("S", 0, 0)
print(f"{oracle_r0.x} {oracle_r0.y}")
oracle_r1 = move("W", 1, 1)
print(f"{oracle_r1.x} {oracle_r1.y}")
oracle_r2 = move("N", -3, -3)
print(f"{oracle_r2.x} {oracle_r2.y}")
oracle_r3 = move("E", -1, 0)
print(f"{oracle_r3.x} {oracle_r3.y}")
oracle_r4 = move("Q", 9, 9)
print(f"{oracle_r4.x} {oracle_r4.y}")
