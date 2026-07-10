function plural(word: string, n: int) -> string {
  if n == 1 {
    "1 " + word
  } else {
    "{n} " + word + "s"
  }
}
