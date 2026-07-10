def sum_list(xs: list[int]) -> int:
    total = 0
    for x in xs:
        total += x
    return total

def max_list(xs: list[int]) -> int:
    max_val = xs[0]
    for x in xs:
        if x > max_val:
            max_val = x
    return max_val

def report(xs: list[int]) -> str:
    s = sum_list(xs)
    m = max_list(xs)
    return f"sum={s} max={m}"
