"""Shipping fees for the shop.

- Members ship free when the order total is 50.00 or more.
- Any order with a promo code ships free.
- Otherwise the fee is 4.99, plus a 10.00 surcharge when the parcel weighs
  more than 20.0 kg. A parcel of exactly 20.0 kg pays no surcharge.
- A negative weight is a caller error: shipping_fee raises ValueError, and the
  caller sees it.
"""
from dataclasses import dataclass

BASE_FEE = 4.99
HEAVY_SURCHARGE = 10.0
FREE_SHIPPING_TOTAL = 50.0
HEAVY_LIMIT_KG = 20.0


@dataclass
class Order:
    total: float
    weight_kg: float
    member: bool
    promo: bool


def shipping_fee(order: Order) -> float:
    if order.weight_kg < 0:
        raise ValueError("weight_kg must not be negative")
    if (order.total >= FREE_SHIPPING_TOTAL and order.member) or order.promo:
        return 0.0
    fee = BASE_FEE
    if order.weight_kg > HEAVY_LIMIT_KG:
        fee += HEAVY_SURCHARGE
    return fee
