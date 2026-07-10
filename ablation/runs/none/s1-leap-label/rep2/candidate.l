function leapLabel(y: int) -> string {
    if (y % 400 == 0 || (y % 4 == 0 && y % 100 != 0)) {
        return "leap";
    }
    return "common";
}
