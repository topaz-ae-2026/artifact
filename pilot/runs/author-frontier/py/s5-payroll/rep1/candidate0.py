def overtime_hours(hours: int) -> int:
    return max(0, hours - 40)


def pay(hours: int, rate: int) -> int:
    overtime = overtime_hours(hours)
    regular = hours - overtime
    return regular * rate + overtime * rate * 2
