def overtime(hours: int) -> int:
    return max(0, hours - 40)

def pay(hours: int, rate: int) -> int:
    regular_hours = min(hours, 40)
    regular_pay = regular_hours * rate
    overtime_hours = overtime(hours)
    overtime_pay = overtime_hours * rate * 2
    return regular_pay + overtime_pay
