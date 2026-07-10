def overtime_hours(hours: int) -> int:
    return max(0, hours - 40)

def pay(hours: int, rate: int) -> int:
    regular_hours = min(hours, 40)
    overtime = overtime_hours(hours)
    return regular_hours * rate + overtime * rate * 2

print(pay(41, 1))
print(pay(60, 5))
print(pay(39, 20))
print(pay(50, 10))
print(pay(40, 1))
