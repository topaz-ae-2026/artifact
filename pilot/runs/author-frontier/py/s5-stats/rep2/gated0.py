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

print(report([0, 0, 0]))
print(report([10, 20, 30]))
print(report([7]))
print(report([2, 9, 4, 9]))
print(report([1, 1, 1, 1, 1]))
