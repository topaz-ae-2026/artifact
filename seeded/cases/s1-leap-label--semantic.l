function leapLabel(y: int) -> string {
    if y / 400 == 0 {
        return "leap"
    }
    if y % 100 == 0 {
        return "common"
    }
    if y % 4 == 0 {
        return "leap"
    }
    return "common"
}
