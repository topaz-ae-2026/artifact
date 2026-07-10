function sumEvens(xs: Array<int>) -> int {
    let sum: int = 0;
    for (x: int in xs) {
        if (x % 2 == 0) {
            sum = sum + x;
        }
    }
    return sum;
}

print("{sumEvens([2, 4, 6])}")
print("{sumEvens([0])}")
print("{sumEvens([1, 3, 5])}")
print("{sumEvens([10, 11, 12, 13, 14])}")
print("{sumEvens([8])}")
