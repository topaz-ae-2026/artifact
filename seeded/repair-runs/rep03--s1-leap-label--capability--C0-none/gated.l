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

print(leapLabel(2023))
print(leapLabel(1600))
print(leapLabel(2100))
print(leapLabel(4))
print(leapLabel(1))
