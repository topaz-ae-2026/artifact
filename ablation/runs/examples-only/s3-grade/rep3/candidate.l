function grade(score: int) -> string {
    return match score {
        case x if x >= 90 => "A"
        case x if x >= 80 => "B"
        case x if x >= 70 => "C"
        case x if x >= 60 => "D"
        case _ => "F"
    }
}
