def array_sum(xs: list[int]) -> int:
    total = 0
    for value in xs:
        total += value
    return total


def array_max(xs: list[int]) -> int:
    maximum = xs[0]
    for value in xs[1:]:
        if value > maximum:
            maximum = value
    return maximum


def report(xs: list[int]) -> str:
    return f"sum={array_sum(xs)} max={array_max(xs)}"
