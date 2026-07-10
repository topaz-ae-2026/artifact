function bucket(n: int) -> string {
    match n {
        case v if v < 0 => "neg"
        case 0 => "zero"
        case _ => "pos"
    }
}
print(bucket(-5))
print(bucket(0))
print(bucket(5))
