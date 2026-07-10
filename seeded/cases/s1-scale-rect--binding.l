function scale(r: { w: int, h: int }, k: int) -> { w: int, h: int } {
    return { w: zz_undef_name.w * k, h: r.h * k }
}
