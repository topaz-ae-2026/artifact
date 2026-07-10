def sum_to(n: int) -> int:
    total = 0
    for k in range(1, n + 1):
        total += k
    return total

print(sum_to(10))
print(sum_to(2))
print(sum_to(100))
print(sum_to(3))
print(sum_to(7))
