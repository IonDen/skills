"""Test suite for shipping.py"""
import pytest
from shipping import Order, shipping_fee, BASE_FEE, HEAVY_SURCHARGE


class TestMemberFreeShipping:
    """Test free shipping for members with sufficient order total."""

    def test_member_high_order_ships_free(self):
        order = Order(total=50.0, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_very_high_order_ships_free(self):
        order = Order(total=100.0, weight_kg=25.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_exact_threshold_ships_free(self):
        order = Order(total=50.0, weight_kg=0.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_below_threshold_pays_base_fee(self):
        order = Order(total=49.99, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_member_below_threshold_heavy_pays_with_surcharge(self):
        order = Order(total=49.99, weight_kg=25.0, member=True, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE


class TestPromoCode:
    """Test free shipping with promo code."""

    def test_promo_code_ships_free(self):
        order = Order(total=0.0, weight_kg=50.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_code_free_despite_non_member_low_order(self):
        order = Order(total=1.0, weight_kg=100.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_code_trumps_member_status(self):
        order = Order(total=30.0, weight_kg=30.0, member=True, promo=True)
        assert shipping_fee(order) == 0.0


class TestNonMemberStandardShipping:
    """Test standard shipping fees for non-members."""

    def test_non_member_light_order_base_fee(self):
        order = Order(total=30.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_non_member_heavy_order_with_surcharge(self):
        order = Order(total=100.0, weight_kg=25.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_non_member_low_order_base_fee(self):
        order = Order(total=10.0, weight_kg=5.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE


class TestWeightThreshold:
    """Test weight-based surcharge logic."""

    def test_weight_exactly_at_limit_no_surcharge(self):
        order = Order(total=10.0, weight_kg=20.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_weight_just_over_limit_applies_surcharge(self):
        order = Order(total=10.0, weight_kg=20.01, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_weight_significantly_over_limit(self):
        order = Order(total=10.0, weight_kg=100.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_weight_zero_no_surcharge(self):
        order = Order(total=10.0, weight_kg=0.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE


class TestInvalidInput:
    """Test error handling for invalid inputs."""

    def test_negative_weight_raises_value_error(self):
        order = Order(total=50.0, weight_kg=-1.0, member=True, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)

    def test_negative_small_weight_raises_value_error(self):
        order = Order(total=10.0, weight_kg=-0.01, member=False, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)

    def test_large_negative_weight_raises_value_error(self):
        order = Order(total=100.0, weight_kg=-50.0, member=True, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_total_order(self):
        order = Order(total=0.0, weight_kg=5.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_member_zero_total_pays_fee(self):
        order = Order(total=0.0, weight_kg=5.0, member=True, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_very_large_order_total(self):
        order = Order(total=999999.99, weight_kg=15.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_very_large_weight(self):
        order = Order(total=10.0, weight_kg=999.99, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_fractional_weight_just_under_limit(self):
        order = Order(total=10.0, weight_kg=19.99, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_fractional_weight_just_over_limit(self):
        order = Order(total=10.0, weight_kg=20.001, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE
