function scale(r: { w: int, h: int }, k: int) -> { w: int, h: int } {
  { w: r.w * k, h: r.h * k }
}

let oracleR0 = scale({ w: 0, h: 0 }, 9)
print("{oracleR0.w} {oracleR0.h}")
let oracleR1 = scale({ w: 7, h: 2 }, 0)
print("{oracleR1.w} {oracleR1.h}")
let oracleR2 = scale({ w: 3, h: 4 }, 100)
print("{oracleR2.w} {oracleR2.h}")
let oracleR3 = scale({ w: 10, h: 10 }, 10)
print("{oracleR3.w} {oracleR3.h}")
let oracleR4 = scale({ w: 1, h: 6 }, 7)
print("{oracleR4.w} {oracleR4.h}")
