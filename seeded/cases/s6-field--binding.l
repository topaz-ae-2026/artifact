function scale(b: { w: int, h: int, d: int }, k: int) -> { w: int, h: int, d: int } {
    return { w: zz_undef_name.w * k, h: b.h * k, d: b.d * k }
}
