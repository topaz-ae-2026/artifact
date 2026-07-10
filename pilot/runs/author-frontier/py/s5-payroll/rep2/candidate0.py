def overtime_hours(hours: int) -> int:
    return max(hours - 40, 0)


def pay(hours: int, rate: int) -> int:
    overtime: int = overtime_hours(hours)
    regular: int = hours - overtime
    return (regular * rate) + (overtime * rate * 2)
