def sum_helper(xs: list[int]) -> int:
    total = 0
    for x in xs:
        total += x
    return total

def max_helper(xs: list[int]) -> int:
    max_val = xs[0]
    for x in xs[1:]:
        if x > max_val:
            max_val = x
    return max_val

def report(xs: list[int]) -> str:
    s = sum_helper(xs)
    m = max_helper(xs)
    return f"sum={s} max={m}"

print(report([0, 0, 0]))
print(report([10, 20, 30]))
print(report([7]))
print(report([2, 9, 4, 9]))
print(report([1, 1, 1, 1, 1]))
