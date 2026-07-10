function countAbove(xs: Array<int>, t: int) -> int {
    var count: int = 0;
    for (x: int in xs) {
        if (x > t) {
            count = count + 1;
        }
    }
    return count;
}
