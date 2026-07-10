function grade(score: int) -> string {
    return match score {
        case n if n >= 90 => "A"
        case n if n >= 80 => "B"
        case n if n >= 70 => "C"
        case n if n >= 60 => "D"
        case _ => "F"
    }
}
