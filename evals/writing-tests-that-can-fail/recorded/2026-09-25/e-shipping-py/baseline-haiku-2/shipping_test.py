import pytest
from shipping import Order, shipping_fee, BASE_FEE, HEAVY_SURCHARGE, FREE_SHIPPING_TOTAL, HEAVY_LIMIT_KG


class TestFreeShippingMember:
    """Member with sufficient order total gets free shipping."""

    def test_member_total_at_threshold(self):
        order = Order(total=50.0, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_total_above_threshold(self):
        order = Order(total=75.0, weight_kg=30.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_heavy_parcel_at_threshold(self):
        order = Order(total=50.0, weight_kg=100.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_total_below_threshold(self):
        order = Order(total=49.99, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == BASE_FEE


class TestFreeShippingPromo:
    """Any order with promo code ships free."""

    def test_promo_low_total_nonmember(self):
        order = Order(total=10.0, weight_kg=5.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_heavy_parcel_nonmember(self):
        order = Order(total=20.0, weight_kg=100.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_with_member_and_threshold(self):
        order = Order(total=50.0, weight_kg=25.0, member=True, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_zero_total(self):
        order = Order(total=0.0, weight_kg=15.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0


class TestBaseFee:
    """Non-members without promo pay base fee for normal weight parcels."""

    def test_nonmember_no_promo_light_parcel(self):
        order = Order(total=100.0, weight_kg=5.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_nonmember_no_promo_weight_at_limit(self):
        order = Order(total=100.0, weight_kg=20.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_nonmember_low_total_light_parcel(self):
        order = Order(total=10.0, weight_kg=15.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_nonmember_zero_total_light_parcel(self):
        order = Order(total=0.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_nonmember_zero_weight(self):
        order = Order(total=25.0, weight_kg=0.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE


class TestHeavySurcharge:
    """Parcels heavier than 20.0 kg incur a surcharge."""

    def test_heavy_parcel_just_over_limit(self):
        order = Order(total=100.0, weight_kg=20.01, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_heavy_parcel_significantly_over_limit(self):
        order = Order(total=25.0, weight_kg=50.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_very_heavy_parcel(self):
        order = Order(total=10.0, weight_kg=1000.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_nonmember_with_sufficient_total_still_pays_surcharge(self):
        order = Order(total=100.0, weight_kg=25.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE


class TestNegativeWeight:
    """Negative weight raises ValueError."""

    def test_negative_weight_member_with_threshold(self):
        order = Order(total=50.0, weight_kg=-1.0, member=True, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)

    def test_negative_weight_nonmember_with_promo(self):
        order = Order(total=10.0, weight_kg=-5.0, member=False, promo=True)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)

    def test_negative_weight_nonmember_no_promo(self):
        order = Order(total=100.0, weight_kg=-0.01, member=False, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_total_just_below_threshold_member(self):
        order = Order(total=49.99, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_weight_exactly_at_surcharge_limit(self):
        order = Order(total=10.0, weight_kg=20.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_weight_fractionally_over_limit(self):
        order = Order(total=10.0, weight_kg=20.0 + 1e-9, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_member_false_with_threshold_total(self):
        order = Order(total=100.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE

    def test_all_flags_false_with_heavy_parcel(self):
        order = Order(total=1000.0, weight_kg=100.0, member=False, promo=False)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_float_total_precision(self):
        order = Order(total=50.0000001, weight_kg=15.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0
