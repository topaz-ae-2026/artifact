function overtimeHours(hours: int) -> int {
    if (hours > 40) {
        return hours - 40;
    }
    return 0;
}

function pay(hours: int, rate: int) -> int {
    let overtime: int = overtimeHours(hours);
    let regular: int = hours - overtime;
    return regular * rate + overtime * rate * 2;
}
