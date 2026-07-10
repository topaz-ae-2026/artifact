function score(result: string) -> int {
  if (result == "win") {
    return 3;
  }
  if (result == "draw") {
    return 1;
  }
  return 0;
}

function total(results: Array<string>) -> int {
  let points: int = 0;
  for (result: string in results) {
    points = points + score(result);
  }
  return points;
}
