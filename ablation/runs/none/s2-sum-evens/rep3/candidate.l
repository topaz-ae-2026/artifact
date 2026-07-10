function sumEvens(xs: Array<int>) -> int {
    var sum: int = 0;
    for (x: int in xs) {
        if (x % 2 == 0) {
            sum = sum + x;
        }
    }
    return sum;
}
