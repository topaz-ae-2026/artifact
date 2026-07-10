def leap_label(y: int) -> str:
    if y % 400 == 0:
        return "leap"
    elif y % 100 == 0:
        return "common"
    elif y % 4 == 0:
        return "leap"
    else:
        return "common"

print(leap_label(2023))
print(leap_label(1600))
print(leap_label(2100))
print(leap_label(4))
print(leap_label(1))
