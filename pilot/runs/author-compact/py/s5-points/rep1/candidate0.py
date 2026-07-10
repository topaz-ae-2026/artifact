def score_result(result: str) -> int:
    if result == "win":
        return 3
    elif result == "draw":
        return 1
    else:
        return 0

def total(results: list[str]) -> int:
    return sum(score_result(r) for r in results)
