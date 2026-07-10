fn grade(score: i32) -> &'static str {
    match score {
        s if s >= 90 => "A",
        s if s >= 80 => "B",
        s if s >= 70 => "C",
        s if s >= 60 => "D",
        _ => "F",
    }
}

fn main() {
    println!("{{reflect}}");
}

print(grade(90))
print(grade(89))
print(grade(60))
print(grade(59))
print(grade(100))
