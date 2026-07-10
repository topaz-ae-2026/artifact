def tax(income: int) -> int:
    if income <= 1000:
        return 0
    if income <= 5000:
        return income - 1000
    return 4000 + 3 * (income - 5000)
