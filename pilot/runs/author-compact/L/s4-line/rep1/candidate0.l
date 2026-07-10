function line(item: string, qty: int, price: int) -> string {
  let total = qty * price
  "{item} x{qty} = {total}"
}
