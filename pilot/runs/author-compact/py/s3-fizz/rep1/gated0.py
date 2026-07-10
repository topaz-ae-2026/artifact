def fizz(n: int) -> str:
    if n % 15 == 0:
        return "fizzbuzz"
    elif n % 3 == 0:
        return "fizz"
    elif n % 5 == 0:
        return "buzz"
    else:
        return str(n)

print(fizz(15))
print(fizz(30))
print(fizz(9))
print(fizz(10))
print(fizz(1))
