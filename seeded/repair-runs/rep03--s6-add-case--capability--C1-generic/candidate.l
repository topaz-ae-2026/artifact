function move(dir: string, x: int, y: int) -> { x: int, y: int } {
    match dir {
        case "N" => { x: x, y: y + 1 }
        case "S" => { x: x, y: y - 1 }
        case "E" => { x: x + 1, y: y }
        case "W" => { x: x - 1, y: y }
        case _ => { x: x, y: y }
    }
}

let eval = move("N", 0, 0)
print("{eval}")
