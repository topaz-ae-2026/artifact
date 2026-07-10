def sum_evens(xs: list[int]) -> int:
    return sum(x for x in xs if x % 2 == 0)
