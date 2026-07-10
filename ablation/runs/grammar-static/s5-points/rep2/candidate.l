function score(result: string) -> int {
    match result {
        case "win" => 3
        case "draw" => 1
        case _ => 0
    }
}

function total(results: Array<string>) -> int {
    let points = for result in results {
        score(result)
    }

    let mut sum = 0
    for point in points {
        sum += point
    }

    sum
}
