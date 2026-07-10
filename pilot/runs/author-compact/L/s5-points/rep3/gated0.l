function scoreResult(result: string) -> int {
  match result {
    case "win" => 3
    case "draw" => 1
    case _ => 0
  }
}

function total(results: Array<string>) -> int {
  reduce(results, 0, (sum, result) => sum + scoreResult(result))
}

print("{total(["draw"])}")
print("{total(["loss", "loss"])}")
print("{total(["win", "draw", "win"])}")
print("{total(["draw", "draw", "draw", "draw"])}")
print("{total(["loss"])}")
