def count_above(xs: list[int], t: int) -> int:
    return sum(x > t for x in xs)
