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
