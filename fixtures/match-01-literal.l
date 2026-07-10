function name(code: int) -> string {
    match code {
        case 0 => "zero"
        case 1 => "one"
        case _ => "many"
    }
}
print(name(0))
print(name(1))
print(name(9))
