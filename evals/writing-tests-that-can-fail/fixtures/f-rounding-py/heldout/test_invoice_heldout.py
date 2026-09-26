import pytest

from invoice import line_total_cents


@pytest.mark.parametrize("price, qty, discount, expected", [
    (45, 1, 50, 23), (7, 3, 50, 11), (9, 1, 50, 5), (3, 1, 50, 2),
    (1000, 2, 25, 1500), (80, 1, 100, 0), (199, 1, 0, 199),
    (199, 1, 10, 179), (13, 1, 90, 1),
])
def test_half_up(price, qty, discount, expected):
    assert line_total_cents(price, qty, discount) == expected


def test_negative_discount_rejected():
    with pytest.raises(ValueError):
        line_total_cents(100, 1, -1)
