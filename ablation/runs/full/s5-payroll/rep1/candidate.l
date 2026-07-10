function overtimeHours(hours: int) -> int {
    if hours > 40 {
        hours - 40
    } else {
        0
    }
}

function pay(hours: int, rate: int) -> int {
    let overtime = overtimeHours(hours)
    (hours - overtime) * rate + overtime * rate * 2
}
