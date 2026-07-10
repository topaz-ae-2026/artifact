function overtime(hours: int) -> int {
    if (hours > 40) {
        return hours - 40;
    }
    return 0;
}

function pay(hours: int, rate: int) -> int {
    let extra: int = overtime(hours);
    return (hours - extra) * rate + extra * rate * 2;
}
