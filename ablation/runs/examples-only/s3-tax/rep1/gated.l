function tax(income: int) -> int {
    if income <= 1000 {
        return 0
    }
    if income <= 5000 {
        return income - 1000
    }
    return 4000 + 3 * (income - 5000)
}

print("{tax(1000)}")
print("{tax(1001)}")
print("{tax(5000)}")
print("{tax(5001)}")
print("{tax(10000)}")
