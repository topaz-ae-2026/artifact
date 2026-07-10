function greet(name: string, hour: int) -> int {
    if hour < 12 {
        return "Good morning, {name}"
    }
    if hour < 18 {
        return "Good afternoon, {name}"
    }
    return "Good evening, {name}"
}
