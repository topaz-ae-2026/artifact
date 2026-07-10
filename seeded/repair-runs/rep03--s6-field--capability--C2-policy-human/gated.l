function scale(b: { w: int, h: int, d: int }, k: int) -> { w: int, h: int, d: int } {
    return { w: b.w * k, h: b.h * k, d: b.d * k }
}

print("{{reflect}}")

let oracleR0 = scale({ w: 7, h: 7, d: 7 }, 0)
print("{oracleR0.w} {oracleR0.h} {oracleR0.d}")
let oracleR1 = scale({ w: 1, h: 2, d: 3 }, 10)
print("{oracleR1.w} {oracleR1.h} {oracleR1.d}")
let oracleR2 = scale({ w: 4, h: 0, d: 6 }, 5)
print("{oracleR2.w} {oracleR2.h} {oracleR2.d}")
let oracleR3 = scale({ w: 3, h: 3, d: 3 }, 3)
print("{oracleR3.w} {oracleR3.h} {oracleR3.d}")
let oracleR4 = scale({ w: 10, h: 1, d: 1 }, 7)
print("{oracleR4.w} {oracleR4.h} {oracleR4.d}")
