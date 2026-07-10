def overtime_hours(hours: int) -> int:
    return max(hours - 40, 0)


def pay(hours: int, rate: int) -> int:
    overtime: int = overtime_hours(hours)
    regular: int = hours - overtime
    return (regular * rate) + (overtime * rate * 2)

print(pay(41, 1))
print(pay(60, 5))
print(pay(39, 20))
print(pay(50, 10))
print(pay(40, 1))
