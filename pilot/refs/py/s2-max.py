def max_of(xs: list[int]) -> int:
    best = xs[0]
    for k in range(1, len(xs)):
        if xs[k] > best:
            best = xs[k]
    return best
