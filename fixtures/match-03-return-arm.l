function sign(n: int) -> int {
    match n {
        case 0 => return 0
        case v if v > 0 => return 1
        case _ => return -1
    }
}
print("{sign(42)} {sign(0)} {sign(-9)}")
