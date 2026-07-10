function badness(target: int, used: int) -> int {
    let slack = target - used
    return slack * slack
}
function total(a: int, b: int) -> int {
    return badness(10, a) + badness(10, b)
}
print("{total(7, 4)}")
