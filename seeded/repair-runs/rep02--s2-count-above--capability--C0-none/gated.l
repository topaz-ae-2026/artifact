fn countAbove(xs: &[i32], t: i32) -> i32 {
    let mut n = 0;
    for &x in xs {
        if x > t {
            n += 1;
        }
    }
    n
}

fn main() {
    print!("{{eval}}");
}

print("{countAbove([10, 20, 30], 15)}")
print("{countAbove([-5, 0, 5], -1)}")
print("{countAbove([1], 0)}")
print("{countAbove([2, 2, 2, 2], 1)}")
print("{countAbove([9, 8, 7], 10)}")
