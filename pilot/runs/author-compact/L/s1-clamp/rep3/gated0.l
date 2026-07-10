function clamp(n: int, lo: int, hi: int) -> int {
  if n < lo {
    lo
  } else if n > hi {
    hi
  } else {
    n
  }
}

print("{clamp(0, 0, 10)}")
print("{clamp(10, 0, 10)}")
print("{clamp(7, 7, 7)}")
print("{clamp(-100, -50, 50)}")
print("{clamp(11, 0, 10)}")
