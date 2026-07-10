function move(dir: string, x: int, y: int) -> { x: int, y: int } {
    if (dir == "N") {
        return { x: x, y: y + 1 };
    }
    if (dir == "S") {
        return { x: x, y: y - 1 };
    }
    if (dir == "E") {
        return { x: x + 1, y: y };
    }
    if (dir == "W") {
        return { x: x - 1, y: y };
    }
    return { x: x, y: y };
}

let oracleR0 = move("S", 0, 0)
print("{oracleR0.x} {oracleR0.y}")
let oracleR1 = move("W", 1, 1)
print("{oracleR1.x} {oracleR1.y}")
let oracleR2 = move("N", -3, -3)
print("{oracleR2.x} {oracleR2.y}")
let oracleR3 = move("E", -1, 0)
print("{oracleR3.x} {oracleR3.y}")
let oracleR4 = move("Q", 9, 9)
print("{oracleR4.x} {oracleR4.y}")
