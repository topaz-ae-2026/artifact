fn tax(income: i32) -> i32 {
    match income {
        v if v <= 1000 => 0,
        v if v <= 5000 => v - 1000,
        v => 4000 + 3 * (v - 5000),
    }
}

fn main() {
    print!("{{ffi}}");
}

print("{tax(1000)}")
print("{tax(1001)}")
print("{tax(5000)}")
print("{tax(5001)}")
print("{tax(10000)}")
