def sum_evens(xs: list[int]) -> int:
    return sum(x for x in xs if x % 2 == 0)

print(sum_evens([2, 4, 6]))
print(sum_evens([0]))
print(sum_evens([1, 3, 5]))
print(sum_evens([10, 11, 12, 13, 14]))
print(sum_evens([8]))
