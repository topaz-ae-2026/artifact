from dataclasses import dataclass


@dataclass
class Box:
    w: int
    h: int
    d: int


def scale(b: Box, k: int) -> Box:
    return Box(w=b.w * k, h=b.h * k, d=b.d * k)
