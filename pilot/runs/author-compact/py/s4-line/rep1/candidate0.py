def line(item: str, qty: int, price: int) -> str:
    total = qty * price
    return f"{item} x{qty} = {total}"
