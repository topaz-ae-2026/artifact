def array_sum(xs: list[int]) -> int:
    total = 0
    for x in xs:
        total += x
    return total


def array_max(xs: list[int]) -> int:
    maximum = xs[0]
    for x in xs[1:]:
        if x > maximum:
            maximum = x
    return maximum


def report(xs: list[int]) -> str:
    return f"sum={array_sum(xs)} max={array_max(xs)}"
