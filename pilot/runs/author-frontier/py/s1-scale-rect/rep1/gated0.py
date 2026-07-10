from dataclasses import dataclass


@dataclass
class Rect:
    w: int
    h: int


def scale(r: Rect, k: int) -> Rect:
    return Rect(w=r.w * k, h=r.h * k)

oracle_r0 = scale(Rect(w=0, h=0), 9)
print(f"{oracle_r0.w} {oracle_r0.h}")
oracle_r1 = scale(Rect(w=7, h=2), 0)
print(f"{oracle_r1.w} {oracle_r1.h}")
oracle_r2 = scale(Rect(w=3, h=4), 100)
print(f"{oracle_r2.w} {oracle_r2.h}")
oracle_r3 = scale(Rect(w=10, h=10), 10)
print(f"{oracle_r3.w} {oracle_r3.h}")
oracle_r4 = scale(Rect(w=1, h=6), 7)
print(f"{oracle_r4.w} {oracle_r4.h}")
