def format_jpy(amount) -> str:
    if amount is None:
        amount = 0
    try:
        value = float(amount)
    except (TypeError, ValueError):
        value = 0.0
    return f"¥{value:,.0f}"
