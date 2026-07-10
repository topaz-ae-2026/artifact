def sum_evens(xs: list[int]) -> int:
    total = 0
    for x in xs:
        if x % 2 == 0:
            total += x
    return total
