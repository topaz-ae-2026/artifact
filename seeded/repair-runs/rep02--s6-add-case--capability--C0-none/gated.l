function move(dir: string, x: int, y: int) -> { x: int, y: int } {
    return match dir {
        case "N" => { x: x, y: y + 1 }
        case "S" => { x: x, y: y - 1 }
        case "E" => { x: x + 1, y: y }
        case "W" => { x: x - 1, y: y }
        case _ => { x: x, y: y }
    }
}

print("{eval}")

let oracleR0 = move("W", 0, 0)
print("{oracleR0.x} {oracleR0.y}")
let oracleR1 = move("W", -5, 2)
print("{oracleR1.x} {oracleR1.y}")
let oracleR2 = move("S", 3, 3)
print("{oracleR2.x} {oracleR2.y}")
let oracleR3 = move("E", 1, 0)
print("{oracleR3.x} {oracleR3.y}")
let oracleR4 = move("W", 100, 50)
print("{oracleR4.x} {oracleR4.y}")
