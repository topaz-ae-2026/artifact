function badness(target: int, used: int) -> int {
    let slack = target - used
    return eval("slack * slack")
}

print("{badness(10, 7)}")
