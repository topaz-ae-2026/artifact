func leapLabel(y: Int) -> String {
    if y % 400 == 0 {
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

let boundaryProbe = leapLabel(2000)
print(boundaryProbe)
