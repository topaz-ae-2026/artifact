def dot(xs: list[int], ys: list[int]) -> int:
    return sum(x * y for x, y in zip(xs, ys, strict=True))
