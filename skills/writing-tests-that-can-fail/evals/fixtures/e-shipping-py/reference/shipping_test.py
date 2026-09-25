"""Reference suite for shipping.py: partitions, 3-value boundaries, one pair
per condition, the error path. No tests of the data holder itself."""
import pytest

from shipping import Order, shipping_fee


def order(total=10.0, weight_kg=1.0, member=False, promo=False):
    return Order(total=total, weight_kg=weight_kg, member=member, promo=promo)


@pytest.mark.parametrize("total, member, promo, expected", [
    (50.0, True, False, 0.0),     # exactly at the threshold, member
    (50.01, True, False, 0.0),    # just above
    (49.99, True, False, 4.99),   # just below
    (50.0, False, False, 4.99),   # membership alone flips the outcome
    (49.99, True, True, 0.0),     # promo alone flips it
    (10.0, False, True, 0.0),     # promo without membership
])
def test_free_shipping_rules(total, member, promo, expected):
    assert shipping_fee(order(total=total, member=member, promo=promo)) == pytest.approx(expected)


@pytest.mark.parametrize("weight, expected", [(19.99, 4.99), (20.0, 4.99), (20.01, 14.99)])
def test_heavy_surcharge_starts_above_20_kg(weight, expected):
    assert shipping_fee(order(weight_kg=weight)) == pytest.approx(expected)


def test_free_shipping_ignores_weight():
    assert shipping_fee(order(total=60.0, member=True, weight_kg=35.0)) == 0.0


def test_negative_weight_is_rejected():
    with pytest.raises(ValueError):
        shipping_fee(order(weight_kg=-0.1))
