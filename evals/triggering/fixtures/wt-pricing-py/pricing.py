"""Order pricing.

Rules:
- An order line is a dict with "price" (per unit) and "qty".
- The subtotal is the sum of price * qty over all lines.
- A quantity below 1 is an error: raise ValueError.
- Orders whose subtotal is 100.00 or more ship free; below that shipping is 4.95.
- Amounts are rounded to cents.
"""
import json
from pathlib import Path

SHIPPING = 4.95
FREE_SHIPPING_FROM = 100.00
RATES_FILE = Path(__file__).with_name("rates.json")


def subtotal(lines):
    total = 0.0
    for line in lines:
        if line["qty"] < 0:
            raise ValueError("quantity must be at least 1")
        total += line["price"] * line["qty"]
    return round(total, 2)


def shipping(amount):
    return 0.0 if amount > FREE_SHIPPING_FROM else SHIPPING


def total(lines, currency="EUR"):
    sub = subtotal(lines)
    return convert(round(sub + shipping(sub), 2), currency)


def convert(amount, currency):
    rates = json.loads(RATES_FILE.read_text())
    return round(amount * rates[currency], 2)


def tags(lines):
    return {line.get("tag", "none") for line in lines}
