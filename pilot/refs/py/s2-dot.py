def dot(xs: list[int], ys: list[int]) -> int:
    total = 0
    for k in range(len(xs)):
        total += xs[k] * ys[k]
    return total
