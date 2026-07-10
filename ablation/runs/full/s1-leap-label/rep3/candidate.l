function leapLabel(y: int) -> string {
    if y % 400 == 0 {
        "leap"
    } else if y % 100 == 0 {
        "common"
    } else if y % 4 == 0 {
        "leap"
    } else {
        "common"
    }
}
