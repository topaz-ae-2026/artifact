function scale(r: { w: int, h: int }, k: int) -> { w: int, h: int } {
    return { w: r.w * k, h: r.h * k };
}
