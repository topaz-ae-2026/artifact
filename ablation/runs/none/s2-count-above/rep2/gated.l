function countAbove(xs: Array<int>, t: int) -> int {
    var count: int = 0;
    for (x: int in xs) {
        if (x > t) {
            count = count + 1;
        }
    }
    return count;
}

print("{countAbove([10, 20, 30], 15)}")
print("{countAbove([-5, 0, 5], -1)}")
print("{countAbove([1], 0)}")
print("{countAbove([2, 2, 2, 2], 1)}")
print("{countAbove([9, 8, 7], 10)}")
