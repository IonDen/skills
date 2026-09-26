"""Invoice line totals.

Amounts are whole cents. line_total_cents(unit_price_cents, quantity,
discount_percent) returns the line price after the discount, rounded to whole
cents with half-up rounding: an exact half cent always rounds up
(12.5 -> 13, 0.5 -> 1). The discount must be between 0 and 100 inclusive,
otherwise ValueError.
"""
import math


def line_total_cents(unit_price_cents: int, quantity: int, discount_percent: float) -> int:
    if not 0 <= discount_percent <= 100:
        raise ValueError("discount_percent must be between 0 and 100")
    raw = unit_price_cents * quantity * (100 - discount_percent) / 100
    return math.floor(raw + 0.5)
