def sum_of(xs: list[int]) -> int:
    total = 0
    for x in xs:
        total += x
    return total


def max_of(xs: list[int]) -> int:
    best = xs[0]
    for k in range(1, len(xs)):
        if xs[k] > best:
            best = xs[k]
    return best


def report(xs: list[int]) -> str:
    return f"sum={sum_of(xs)} max={max_of(xs)}"
