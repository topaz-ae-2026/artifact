function countAbove(xs: Array<int>, t: int) -> int {
    reduce(xs, 0, (count, value) => if value > t {
        count + 1
    } else {
        count
    })
}
