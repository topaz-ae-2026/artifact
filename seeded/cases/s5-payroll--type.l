function overtime(hours: int) -> string {
    if hours > 40 {
        return hours - 40
    }
    return 0
}
function pay(hours: int, rate: int) -> int {
    let extra = overtime(hours)
    let normal = hours - extra
    return normal * rate + extra * rate * 2
}
