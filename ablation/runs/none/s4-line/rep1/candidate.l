function line(item: string, qty: int, price: int) -> string {
    return item + " x" + to_string(qty) + " = " + to_string(qty * price);
}
