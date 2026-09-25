"""Tests for shipping.py

Each test is named to describe the bug it catches. Flip a comparison or
constant in shipping.py and watch the appropriate test go red.
"""
import pytest
from shipping import Order, shipping_fee


class TestNegativeWeight:
    """Catches: not checking weight_kg < 0, or returning instead of raising."""

    def test_negative_weight_raises(self):
        order = Order(total=100.0, weight_kg=-0.1, member=False, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)

    def test_negative_weight_large_negative(self):
        order = Order(total=100.0, weight_kg=-50.0, member=False, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)


class TestPromoCodeFreeShipping:
    """Catches: promo not granting free shipping, or promo being AND instead of OR."""

    def test_promo_true_returns_zero_regardless_of_member_or_total(self):
        order = Order(total=10.0, weight_kg=50.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_true_with_heavy_weight_still_free(self):
        order = Order(total=0.0, weight_kg=100.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_true_non_member_low_total_still_free(self):
        order = Order(total=1.0, weight_kg=25.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0


class TestMemberFreeShippingBoundary:
    """Catches: wrong comparison (>= vs >), wrong constant (50.0), or
    missing the member=True requirement."""

    def test_member_total_below_threshold_not_free(self):
        order = Order(total=49.99, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 4.99

    def test_member_total_exactly_fifty_is_free(self):
        order = Order(total=50.0, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_total_above_threshold_is_free(self):
        order = Order(total=50.01, weight_kg=30.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_non_member_total_fifty_not_free(self):
        order = Order(total=50.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_non_member_total_above_threshold_not_free(self):
        order = Order(total=100.0, weight_kg=15.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99


class TestWeightSurchargeBoundary:
    """Catches: wrong comparison (> vs >=), wrong constant (20.0), or
    wrong surcharge amount (10.0)."""

    def test_weight_exactly_twenty_no_surcharge(self):
        order = Order(total=10.0, weight_kg=20.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_weight_just_below_twenty_no_surcharge(self):
        order = Order(total=10.0, weight_kg=19.99, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_weight_just_above_twenty_includes_surcharge(self):
        order = Order(total=10.0, weight_kg=20.01, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_weight_significantly_above_twenty_includes_surcharge(self):
        order = Order(total=10.0, weight_kg=50.0, member=False, promo=False)
        assert shipping_fee(order) == 14.99


class TestBaseFeeAndSurcharge:
    """Catches: wrong base fee (4.99), wrong surcharge (10.0), or arithmetic errors."""

    def test_zero_weight_base_fee_only(self):
        order = Order(total=10.0, weight_kg=0.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_light_weight_base_fee_only(self):
        order = Order(total=10.0, weight_kg=5.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_heavy_weight_base_plus_surcharge(self):
        order = Order(total=10.0, weight_kg=25.0, member=False, promo=False)
        assert shipping_fee(order) == 14.99


class TestConditionCombinations:
    """Catches: operator precedence issues (AND vs OR), or short-circuit logic errors."""

    def test_member_below_threshold_light_weight(self):
        """Member=True but total too low, so no free shipping despite being member."""
        order = Order(total=40.0, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 4.99

    def test_member_below_threshold_heavy_weight(self):
        """Member=True but total too low, so must pay base + surcharge."""
        order = Order(total=40.0, weight_kg=25.0, member=True, promo=False)
        assert shipping_fee(order) == 14.99

    def test_member_at_threshold_heavy_weight_free_anyway(self):
        """Member meets threshold, so free shipping even though weight is heavy."""
        order = Order(total=50.0, weight_kg=50.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_promo_overrides_member_and_total_logic(self):
        """Promo=True makes shipping free regardless of member or total."""
        order = Order(total=1.0, weight_kg=100.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_false_member_false_requires_total_check(self):
        """When both promo and member are False, weight determines fee."""
        order = Order(total=49.99, weight_kg=21.0, member=False, promo=False)
        assert shipping_fee(order) == 14.99


class TestEdgeCases:
    """Catches: off-by-one errors, missing initialization, unhandled edge inputs."""

    def test_zero_total_non_member_no_promo(self):
        order = Order(total=0.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_large_total_non_member_must_pay(self):
        order = Order(total=1000.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_very_heavy_weight(self):
        order = Order(total=10.0, weight_kg=1000.0, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_fractional_weight_below_boundary(self):
        order = Order(total=10.0, weight_kg=20.001, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_fractional_total_close_to_threshold(self):
        order = Order(total=49.999, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 4.99
