def count_above(xs: list[int], t: int) -> int:
    return sum(1 for x in xs if x > t)

print(count_above([10, 20, 30], 15))
print(count_above([-5, 0, 5], -1))
print(count_above([1], 0))
print(count_above([2, 2, 2, 2], 1))
print(count_above([9, 8, 7], 10))
