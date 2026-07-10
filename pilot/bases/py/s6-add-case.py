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
    return Point(x=x, y=y)
