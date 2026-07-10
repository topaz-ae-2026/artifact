function move(dir: string, x: int, y: int) -> { x: int, y: int } {
    match zz_undef_name {
        case "N" => { x: x, y: y + 1 }
        case "S" => { x: x, y: y - 1 }
        case "E" => { x: x + 1, y: y }
        case "W" => { x: x - 1, y: y }
        case _ => { x: x, y: y }
    }
}
