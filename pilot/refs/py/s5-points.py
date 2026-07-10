def score(result: str) -> int:
    if result == "win":
        return 3
    if result == "draw":
        return 1
    return 0


def total(results: list[str]) -> int:
    points = 0
    for r in results:
        points += score(r)
    return points
