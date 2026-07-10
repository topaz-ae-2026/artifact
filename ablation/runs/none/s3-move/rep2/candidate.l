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
