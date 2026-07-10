function grow(size: { w: int, h: int }, delta: int) -> { w: int, h: int } {
    return { w: size.w + delta, h: size.h + delta }
}
let s = grow({ w: 2, h: 3 }, 4)
print("{s.w} {s.h}")
