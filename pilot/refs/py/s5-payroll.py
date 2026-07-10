def overtime(hours: int) -> int:
    if hours > 40:
        return hours - 40
    return 0


def pay(hours: int, rate: int) -> int:
    extra = overtime(hours)
    normal = hours - extra
    return normal * rate + extra * rate * 2
