def overtime_hours(hours: int) -> int:
    return max(0, hours - 40)

def pay(hours: int, rate: int) -> int:
    ot_hours = overtime_hours(hours)
    regular_hours = hours - ot_hours
    return regular_hours * rate + ot_hours * rate * 2

print(pay(41, 1))
print(pay(60, 5))
print(pay(39, 20))
print(pay(50, 10))
print(pay(40, 1))
