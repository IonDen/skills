import pytest
from shipping import shipping_fee, Order


class TestFreeShippingPromo:
    """Free shipping when any order has a promo code."""

    def test_promo_free_shipping_nonmember_low_total(self):
        order = Order(total=10.0, weight_kg=5.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_free_shipping_nonmember_heavy(self):
        order = Order(total=30.0, weight_kg=50.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_free_shipping_member_low_total(self):
        order = Order(total=30.0, weight_kg=5.0, member=True, promo=True)
        assert shipping_fee(order) == 0.0


class TestFreeShippingMember:
    """Free shipping for members when order total >= 50.00."""

    def test_member_free_at_threshold(self):
        order = Order(total=50.0, weight_kg=5.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_free_above_threshold(self):
        order = Order(total=100.0, weight_kg=5.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_free_heavy_at_threshold(self):
        order = Order(total=50.0, weight_kg=50.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_member_not_free_below_threshold(self):
        order = Order(total=49.99, weight_kg=5.0, member=True, promo=False)
        assert shipping_fee(order) == 4.99

    def test_member_not_free_just_below_threshold(self):
        order = Order(total=49.99, weight_kg=30.0, member=True, promo=False)
        assert shipping_fee(order) == 14.99


class TestBaseFee:
    """Base fee of 4.99 applies for non-eligible orders under weight limit."""

    def test_nonmember_light_no_promo(self):
        order = Order(total=100.0, weight_kg=5.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_nonmember_zero_total(self):
        order = Order(total=0.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_nonmember_at_weight_limit(self):
        order = Order(total=100.0, weight_kg=20.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_member_below_threshold_light(self):
        order = Order(total=49.99, weight_kg=5.0, member=True, promo=False)
        assert shipping_fee(order) == 4.99


class TestHeavySurcharge:
    """10.00 surcharge added when weight > 20.0 kg."""

    def test_heavy_surcharge_just_over_limit(self):
        order = Order(total=100.0, weight_kg=20.01, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_heavy_surcharge_well_over_limit(self):
        order = Order(total=100.0, weight_kg=50.0, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_no_surcharge_at_limit(self):
        order = Order(total=100.0, weight_kg=20.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_no_surcharge_just_under_limit(self):
        order = Order(total=100.0, weight_kg=19.99, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_heavy_surcharge_member_below_threshold(self):
        order = Order(total=30.0, weight_kg=25.0, member=True, promo=False)
        assert shipping_fee(order) == 14.99


class TestWeightBoundary:
    """Boundary tests for weight limit at 20.0 kg."""

    def test_weight_exactly_20kg(self):
        order = Order(total=10.0, weight_kg=20.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_weight_20kg_plus_epsilon(self):
        order = Order(total=10.0, weight_kg=20.0 + 1e-10, member=False, promo=False)
        assert shipping_fee(order) == 14.99

    def test_weight_zero(self):
        order = Order(total=10.0, weight_kg=0.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99


class TestTotalBoundary:
    """Boundary tests for member free shipping at 50.00."""

    def test_total_exactly_50(self):
        order = Order(total=50.0, weight_kg=30.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0

    def test_total_just_below_50(self):
        order = Order(total=49.99, weight_kg=30.0, member=True, promo=False)
        assert shipping_fee(order) == 14.99

    def test_total_just_above_50(self):
        order = Order(total=50.01, weight_kg=30.0, member=True, promo=False)
        assert shipping_fee(order) == 0.0


class TestNegativeWeight:
    """Negative weight raises ValueError."""

    def test_negative_weight_raises_error(self):
        order = Order(total=10.0, weight_kg=-1.0, member=False, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)

    def test_negative_weight_member_raises_error(self):
        order = Order(total=100.0, weight_kg=-5.0, member=True, promo=False)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)

    def test_negative_weight_promo_raises_error(self):
        order = Order(total=10.0, weight_kg=-0.1, member=False, promo=True)
        with pytest.raises(ValueError, match="weight_kg must not be negative"):
            shipping_fee(order)


class TestConditionCombinations:
    """Tests to verify condition pairs that differ in one variable."""

    def test_promo_vs_no_promo_same_member_total_weight(self):
        base_order = Order(total=30.0, weight_kg=25.0, member=False, promo=False)
        promo_order = Order(total=30.0, weight_kg=25.0, member=False, promo=True)
        assert shipping_fee(base_order) == 14.99
        assert shipping_fee(promo_order) == 0.0

    def test_member_vs_nonmember_same_total_weight_promo(self):
        nonmember = Order(total=60.0, weight_kg=10.0, member=False, promo=False)
        member = Order(total=60.0, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(nonmember) == 4.99
        assert shipping_fee(member) == 0.0

    def test_light_vs_heavy_same_member_promo_total(self):
        light = Order(total=30.0, weight_kg=15.0, member=False, promo=False)
        heavy = Order(total=30.0, weight_kg=25.0, member=False, promo=False)
        assert shipping_fee(light) == 4.99
        assert shipping_fee(heavy) == 14.99

    def test_high_total_nonmember_still_charged(self):
        order = Order(total=1000.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99


class TestLogicalOrders:
    """Tests ensuring both member and total matter for free shipping."""

    def test_member_required_with_high_total(self):
        """Non-member doesn't get free shipping even with total >= 50."""
        order = Order(total=100.0, weight_kg=10.0, member=False, promo=False)
        assert shipping_fee(order) == 4.99

    def test_total_threshold_required_for_members(self):
        """Member doesn't get free shipping if total < 50, without promo."""
        order = Order(total=49.99, weight_kg=10.0, member=True, promo=False)
        assert shipping_fee(order) == 4.99

    def test_promo_overrides_all(self):
        """Promo code overrides both member status and total requirement."""
        order = Order(total=1.0, weight_kg=100.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0
