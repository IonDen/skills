import pytest

from invoice import line_total_cents


def test_full_price():
    assert line_total_cents(199, 3, 0) == 597


def test_half_cent_rounds_up():
    assert line_total_cents(25, 1, 50) == 13


def test_tiny_line_still_rounds_up():
    assert line_total_cents(5, 1, 90) == 1


def test_discount_out_of_range():
    with pytest.raises(ValueError):
        line_total_cents(100, 1, 101)
