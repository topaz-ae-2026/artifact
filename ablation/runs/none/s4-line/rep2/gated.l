function line(item: string, qty: int, price: int) -> string {
    return item + " x" + qty + " = " + (qty * price);
}

print(line("우유", 2, 1200))
print(line("kit", 10, 7))
print(line("z", 1, 1))
print(line("gum", 7, 0))
print(line("t", 100, 100))
