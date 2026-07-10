def leap_label(y: int) -> str:
    if y % 400 == 0 or (y % 4 == 0 and y % 100 != 0):
        return "leap"
    return "common"
