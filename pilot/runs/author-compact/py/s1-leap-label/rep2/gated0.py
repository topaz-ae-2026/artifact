def leap_label(y: int) -> str:
    return "leap" if (y % 400 == 0 or (y % 4 == 0 and y % 100 != 0)) else "common"

print(leap_label(2023))
print(leap_label(1600))
print(leap_label(2100))
print(leap_label(4))
print(leap_label(1))
