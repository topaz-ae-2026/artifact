def dot(xs: list[int], ys: list[int]) -> int:
    return sum(x * y for x, y in zip(xs, ys))

print(dot([1, 1, 1], [2, 3, 4]))
print(dot([0, 9], [7, 0]))
print(dot([2, 3], [4, 5]))
print(dot([-1, 2], [3, 4]))
print(dot([10], [10]))
