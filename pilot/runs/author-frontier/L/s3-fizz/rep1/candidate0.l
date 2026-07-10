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
