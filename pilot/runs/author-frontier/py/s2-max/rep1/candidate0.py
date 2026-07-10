def max_of(xs: list[int]) -> int:
    largest = xs[0]
    for value in xs[1:]:
        if value > largest:
            largest = value
    return largest
