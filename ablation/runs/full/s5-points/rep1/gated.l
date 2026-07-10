function score(result: string) -> int {
    match result {
        case "win" => 3
        case "draw" => 1
        case _ => 0
    }
}

function total(results: Array<string>) -> int {
    reduce(results, 0, (points, result) => points + score(result))
}

print("{total(["draw"])}")
print("{total(["loss", "loss"])}")
print("{total(["win", "draw", "win"])}")
print("{total(["draw", "draw", "draw", "draw"])}")
print("{total(["loss"])}")
