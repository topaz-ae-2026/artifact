function overtimeHours(hours: int) -> int {
    if hours > 40 {
        return hours - 40
    }
    return 0
}

function pay(hours: int, rate: int) -> int {
    let overtime = overtimeHours(hours)
    let regular = hours - overtime
    return regular * rate + overtime * rate * 2
}

print("{pay(41, 1)}")
print("{pay(60, 5)}")
print("{pay(39, 20)}")
print("{pay(50, 10)}")
print("{pay(40, 1)}")
