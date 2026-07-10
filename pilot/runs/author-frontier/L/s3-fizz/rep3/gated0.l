function fizz(n: int) -> string {
    if n % 15 == 0 {
        "fizzbuzz"
    } else if n % 3 == 0 {
        "fizz"
    } else if n % 5 == 0 {
        "buzz"
    } else {
        "{n}"
    }
}

print(fizz(15))
print(fizz(30))
print(fizz(9))
print(fizz(10))
print(fizz(1))
