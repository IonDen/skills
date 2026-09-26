"""Test suite for shipping.py"""
import pytest
from shipping import Order, shipping_fee, BASE_FEE, HEAVY_SURCHARGE, FREE_SHIPPING_TOTAL, HEAVY_LIMIT_KG


class TestFreeShippingMemberThreshold:
    """Tests for free shipping when member with sufficient order total."""

    def test_member_with_exact_threshold_free_shipping(self):
        """Member with order total exactly at 50.00 gets free shipping."""
        order = Order(total=FREE_SHIPPING_TOTAL, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_above_threshold_free_shipping(self):
        """Member with order total above 50.00 gets free shipping."""
        order = Order(total=100.0, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_below_threshold_pays_fee(self):
        """Member with order total below 50.00 pays standard shipping."""
        order = Order(total=49.99, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_non_member_above_threshold_pays_fee(self):
        """Non-member does not get free shipping even with high order total."""
        order = Order(total=100.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE


class TestFreeShippingPromoCode:
    """Tests for free shipping with promo code."""

    def test_promo_code_always_free_regardless_of_total(self):
        """Promo code always results in free shipping."""
        order = Order(total=0.0, weight_kg=10.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_code_free_even_with_heavy_weight(self):
        """Promo code gives free shipping even for heavy parcels."""
        order = Order(total=0.0, weight_kg=100.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_code_free_even_for_non_member(self):
        """Promo code gives free shipping regardless of member status."""
        order = Order(total=10.0, weight_kg=15.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0


class TestBaseShippingFee:
    """Tests for standard base fee calculation."""

    def test_non_member_light_weight_pays_base_fee(self):
        """Non-member with light package pays base fee only."""
        order = Order(total=25.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_base_fee_value(self):
        """Base fee is 4.99."""
        order = Order(total=0.0, weight_kg=5.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99


class TestHeavyParcelSurcharge:
    """Tests for surcharge on parcels heavier than 20.0 kg."""

    def test_weight_above_limit_incurs_surcharge(self):
        """Parcel over 20.0 kg incurs heavy surcharge."""
        order = Order(total=25.0, weight_kg=20.1, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_weight_exactly_at_limit_no_surcharge(self):
        """Parcel of exactly 20.0 kg does not incur surcharge."""
        order = Order(total=25.0, weight_kg=HEAVY_LIMIT_KG, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_weight_well_above_limit_incurs_surcharge(self):
        """Parcel significantly over 20.0 kg incurs surcharge."""
        order = Order(total=25.0, weight_kg=50.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_heavy_surcharge_value(self):
        """Heavy surcharge is 10.00."""
        order = Order(total=25.0, weight_kg=25.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99 + 10.0


class TestNegativeWeightError:
    """Tests for error handling with negative weight."""

    def test_negative_weight_raises_value_error(self):
        """Negative weight raises ValueError."""
        order = Order(total=100.0, weight_kg=-1.0, member=False, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)

    def test_negative_weight_with_free_shipping_conditions_still_raises(self):
        """Even with free shipping conditions, negative weight raises error."""
        order = Order(total=100.0, weight_kg=-5.0, member=True, promo=False)
        with pytest.raises(ValueError):
            shipping_fee(order)

    def test_error_message_content(self):
        """ValueError has correct message."""
        order = Order(total=25.0, weight_kg=-0.5, member=False, promo=False)
        with pytest.raises(ValueError) as exc_info:
            shipping_fee(order)
        assert "weight_kg must not be negative" in str(exc_info.value)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_weight_light_parcel(self):
        """Zero weight is valid and treated as light."""
        order = Order(total=25.0, weight_kg=0.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_zero_total_non_member_pays_fee(self):
        """Order with zero total and non-member pays standard fee."""
        order = Order(total=0.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_very_high_order_total_member_free_shipping(self):
        """Very high order total with member still gets free shipping."""
        order = Order(total=10000.0, weight_kg=100.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_large_weight_no_member_discount(self):
        """Large weight without member/promo incurs surcharge."""
        order = Order(total=1000.0, weight_kg=1000.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_fractional_weights(self):
        """Fractional weights are handled correctly."""
        order = Order(total=25.0, weight_kg=20.01, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

        order2 = Order(total=25.0, weight_kg=19.99, member=False, promo=False)
        assert shipping_fee(order2) == BASE_FEE


class TestComplexScenarios:
    """Tests for combinations of conditions."""

    def test_member_and_promo_both_free(self):
        """Both member with high total and promo code result in free shipping."""
        order = Order(total=100.0, weight_kg=30.0, member=True, promo=True)
        assert shipping_fee(order) == 0.0

    def test_member_with_high_total_but_heavy_still_free(self):
        """Member with high total gets free shipping even with very heavy parcel."""
        order = Order(total=100.0, weight_kg=500.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_promo_overrides_all_conditions(self):
        """Promo code gives free shipping regardless of member or total."""
        order = Order(total=0.01, weight_kg=25.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0
