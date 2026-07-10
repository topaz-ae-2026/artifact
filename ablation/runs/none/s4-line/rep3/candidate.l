function line(item: string, qty: int, price: int) -> string {
    return item + " x" + string(qty) + " = " + string(qty * price);
}
