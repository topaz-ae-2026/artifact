function countAbove(xs: Array<int>, t: int) -> int {
    reduce(xs, 0, (count, value) => if value > t {
        count + 1
    } else {
        count
    })
}

print("{countAbove([10, 20, 30], 15)}")
print("{countAbove([-5, 0, 5], -1)}")
print("{countAbove([1], 0)}")
print("{countAbove([2, 2, 2, 2], 1)}")
print("{countAbove([9, 8, 7], 10)}")
