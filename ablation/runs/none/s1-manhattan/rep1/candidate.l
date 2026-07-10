function dist(x1: int, y1: int, x2: int, y2: int) -> int {
    return (if x1 >= x2 then x1 - x2 else x2 - x1)
         + (if y1 >= y2 then y1 - y2 else y2 - y1);
}
