function sumEvens(xs: Array<int>) -> int {
    let mut sum = 0
    for x in xs {
        if x % 2 == 0 {
            sum += x
        }
    }
    sum
}

print("{sumEvens([2, 4, 6])}")
print("{sumEvens([0])}")
print("{sumEvens([1, 3, 5])}")
print("{sumEvens([10, 11, 12, 13, 14])}")
print("{sumEvens([8])}")
