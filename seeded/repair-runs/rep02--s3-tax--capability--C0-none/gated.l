function tax(income: int) -> int {
    match income {
        case v if v <= 1000 => 0;
        case v if v <= 5000 => v - 1000;
        case v => 4000 + 3 * (v - 5000);
    }
}

print("{ffi}");

print("{tax(1000)}")
print("{tax(1001)}")
print("{tax(5000)}")
print("{tax(5001)}")
print("{tax(10000)}")
