import pytest
from shipping import Order, shipping_fee


class TestPromoCodeFreeShipping:
    def test_promo_code_grants_free_shipping_non_member_low_total(self):
        # Catches: if promo condition is removed or made and instead of or
        order = Order(total=10.0, weight_kg=25.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_code_grants_free_shipping_member(self):
        # Catches: if promo condition is removed
        order = Order(total=100.0, weight_kg=25.0, member=True, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_code_overrides_weight_surcharge(self):
        # Catches: if weight check is not short-circuited when promo is true
        order = Order(total=1.0, weight_kg=50.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0


class TestMemberFreeShipping:
    def test_member_free_shipping_at_threshold(self):
        # Catches: if >= is changed to >
        order = Order(total=50.0, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_free_shipping_above_threshold(self):
        # Catches: if >= is changed to >
        order = Order(total=50.01, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_free_shipping_well_above_threshold(self):
        # Catches: if >= is changed to >
        order = Order(total=100.0, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_charged_below_threshold(self):
        # Catches: if >= is changed to >
        order = Order(total=49.99, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 4.99

    def test_member_charged_far_below_threshold(self):
        # Catches: if >= is changed to >
        order = Order(total=1.0, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 4.99

    def test_member_charged_with_heavy_weight_below_threshold(self):
        # Catches: if >= is changed to >
        order = Order(total=49.99, weight_kg=25.0, member=True, promo=False)
        assert shipping_fee(order) == 14.99

    def test_member_free_with_heavy_weight_at_threshold(self):
        # Catches: if member discount is removed when weight is high
        order = Order(total=50.0, weight_kg=25.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0


class TestNonMemberFreeShipping:
    def test_non_member_no_discount_with_high_total(self):
        # Catches: if member check is removed
        order = Order(total=100.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_non_member_charged_regardless_of_total(self):
        # Catches: if member check is removed
        order = Order(total=50.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99


class TestBaseFee:
    def test_base_fee_light_weight(self):
        # Catches: if BASE_FEE is wrong or surcharge is wrongly added
        order = Order(total=1.0, weight_kg=5.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_base_fee_zero_weight(self):
        # Catches: if BASE_FEE is wrong or weight boundary is off
        order = Order(total=1.0, weight_kg=0.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99


class TestHeavyWeightSurcharge:
    def test_surcharge_applied_when_weight_exceeds_limit(self):
        # Catches: if > is changed to >=
        order = Order(total=1.0, weight_kg=20.01, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_surcharge_applied_at_high_weight(self):
        # Catches: if surcharge value is wrong or surcharge is not added
        order = Order(total=1.0, weight_kg=25.0, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_surcharge_applied_at_very_high_weight(self):
        # Catches: if surcharge is dropped
        order = Order(total=1.0, weight_kg=100.0, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_no_surcharge_at_exact_limit(self):
        # Catches: if > is changed to >=
        order = Order(total=1.0, weight_kg=20.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_no_surcharge_just_below_limit(self):
        # Catches: if > is changed to >=
        order = Order(total=1.0, weight_kg=19.99, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_no_surcharge_well_below_limit(self):
        # Catches: if surcharge is always added
        order = Order(total=1.0, weight_kg=1.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99


class TestNegativeWeight:
    def test_negative_weight_raises_value_error(self):
        # Catches: if ValueError is not raised
        order = Order(total=1.0, weight_kg=-1.0, member=False, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)

    def test_negative_weight_large_negative_raises(self):
        # Catches: if < 0 check is changed to <= 0
        order = Order(total=1.0, weight_kg=-100.0, member=False, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)


class TestComplexScenarios:
    def test_non_member_light_weight_no_promo(self):
        # Catches: if member or promo condition is wrongly evaluated
        order = Order(total=1.0, weight_kg=5.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_non_member_heavy_weight_no_promo(self):
        # Catches: if weight boundary or surcharge is wrong
        order = Order(total=1.0, weight_kg=30.0, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_member_heavy_weight_at_threshold(self):
        # Catches: if member free shipping short-circuits weight check
        order = Order(total=50.0, weight_kg=30.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_heavy_weight_below_threshold(self):
        # Catches: if member check removes weight surcharge
        order = Order(total=49.99, weight_kg=30.0, member=True, promo=False)
        assert shipping_fee(order) == 14.99

    def test_promo_code_light_weight(self):
        # Catches: if promo condition is not evaluated correctly
        order = Order(total=1.0, weight_kg=5.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0
