function fizz(n: int) -> string {
    if (n % 15 == 0) {
        return "fizzbuzz";
    }
    if (n % 3 == 0) {
        return "fizz";
    }
    if (n % 5 == 0) {
        return "buzz";
    }
    return int_to_string(n);
}

print(fizz(15))
print(fizz(30))
print(fizz(9))
print(fizz(10))
print(fizz(1))
