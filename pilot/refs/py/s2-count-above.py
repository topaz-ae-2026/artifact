def count_above(xs: list[int], t: int) -> int:
    n = 0
    for x in xs:
        if x > t:
            n += 1
    return n
