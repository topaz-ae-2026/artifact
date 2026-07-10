function greet(name: string, hour: int) -> string {
    if (hour < 12) {
        return "Good morning, " + name;
    } else if (hour < 18) {
        return "Good afternoon, " + name;
    } else {
        return "Good evening, " + name;
    }
}
