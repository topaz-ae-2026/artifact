def count_above(xs: list[int], t: int) -> int:
    return sum(1 for x in xs if x > t)
