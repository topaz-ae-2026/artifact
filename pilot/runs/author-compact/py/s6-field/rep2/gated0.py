from dataclasses import dataclass


@dataclass
class Box:
    w: int
    h: int
    d: int


def scale(b: Box, k: int) -> Box:
    return Box(w=b.w * k, h=b.h * k, d=b.d * k)

oracle_r0 = scale(Box(w=7, h=7, d=7), 0)
print(f"{oracle_r0.w} {oracle_r0.h} {oracle_r0.d}")
oracle_r1 = scale(Box(w=1, h=2, d=3), 10)
print(f"{oracle_r1.w} {oracle_r1.h} {oracle_r1.d}")
oracle_r2 = scale(Box(w=4, h=0, d=6), 5)
print(f"{oracle_r2.w} {oracle_r2.h} {oracle_r2.d}")
oracle_r3 = scale(Box(w=3, h=3, d=3), 3)
print(f"{oracle_r3.w} {oracle_r3.h} {oracle_r3.d}")
oracle_r4 = scale(Box(w=10, h=1, d=1), 7)
print(f"{oracle_r4.w} {oracle_r4.h} {oracle_r4.d}")
