def score(result: str) -> int:
    if result == "win":
        return 3
    if result == "draw":
        return 1
    return 0


def total(results: list[str]) -> int:
    return sum(score(result) for result in results)

print(total(["draw"]))
print(total(["loss", "loss"]))
print(total(["win", "draw", "win"]))
print(total(["draw", "draw", "draw", "draw"]))
print(total(["loss"]))
