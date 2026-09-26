"""Invoice line totals.

Amounts are whole cents. line_total_cents(unit_price_cents, quantity,
discount_percent) returns the line price after the discount, rounded to whole
cents with half-up rounding: an exact half cent always rounds up
(12.5 -> 13, 0.5 -> 1). The discount must be between 0 and 100 inclusive,
otherwise ValueError.
"""

from decimal import Decimal, ROUND_HALF_UP


def line_total_cents(unit_price_cents: int, quantity: int, discount_percent: float) -> int:
    if not 0 <= discount_percent <= 100:
        raise ValueError("discount_percent must be between 0 and 100")
    raw = Decimal(unit_price_cents) * Decimal(quantity) * (Decimal(100) - Decimal(discount_percent)) / Decimal(100)
    return int(raw.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
