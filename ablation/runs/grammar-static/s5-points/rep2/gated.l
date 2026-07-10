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

print("{total(["draw"])}")
print("{total(["loss", "loss"])}")
print("{total(["win", "draw", "win"])}")
print("{total(["draw", "draw", "draw", "draw"])}")
print("{total(["loss"])}")
