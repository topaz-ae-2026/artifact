def max_of(xs: list[int]) -> int:
    largest = xs[0]
    for value in xs[1:]:
        if value > largest:
            largest = value
    return largest

print(max_of([0, 0]))
print(max_of([1, 2, 3, 4, 5]))
print(max_of([9, 2, 9]))
print(max_of([-100, -200]))
print(max_of([7, 7, 7]))
