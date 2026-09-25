import pytest

from shipping import (
    BASE_FEE,
    FREE_SHIPPING_TOTAL,
    HEAVY_LIMIT_KG,
    HEAVY_SURCHARGE,
    Order,
    shipping_fee,
)


def make_order(total=10.0, weight_kg=1.0, member=False, promo=False):
    return Order(total=total, weight_kg=weight_kg, member=member, promo=promo)


class TestFreeShipping:
    def test_member_with_total_above_threshold_ships_free(self):
        order = make_order(total=FREE_SHIPPING_TOTAL + 1, weight_kg=1.0, member=True)
        assert shipping_fee(order) == 0.0

    def test_member_with_total_exactly_at_threshold_ships_free(self):
        order = make_order(total=FREE_SHIPPING_TOTAL, weight_kg=1.0, member=True)
        assert shipping_fee(order) == 0.0

    def test_member_with_total_below_threshold_does_not_ship_free(self):
        order = make_order(total=FREE_SHIPPING_TOTAL - 0.01, weight_kg=1.0, member=True)
        assert shipping_fee(order) == BASE_FEE

    def test_non_member_with_total_above_threshold_does_not_ship_free(self):
        order = make_order(total=FREE_SHIPPING_TOTAL + 1, weight_kg=1.0, member=False)
        assert shipping_fee(order) == BASE_FEE

    def test_promo_code_ships_free_regardless_of_total_or_membership(self):
        order = make_order(total=0.0, weight_kg=1.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_promo_code_ships_free_even_when_heavy(self):
        order = make_order(total=0.0, weight_kg=100.0, member=False, promo=True)
        assert shipping_fee(order) == 0.0

    def test_member_and_promo_both_true_ships_free(self):
        order = make_order(total=FREE_SHIPPING_TOTAL, weight_kg=1.0, member=True, promo=True)
        assert shipping_fee(order) == 0.0


class TestFeeCalculation:
    def test_light_parcel_pays_base_fee_only(self):
        order = make_order(total=10.0, weight_kg=1.0)
        assert shipping_fee(order) == BASE_FEE

    def test_zero_weight_pays_base_fee_only(self):
        order = make_order(total=10.0, weight_kg=0.0)
        assert shipping_fee(order) == BASE_FEE

    def test_weight_exactly_at_heavy_limit_pays_no_surcharge(self):
        order = make_order(total=10.0, weight_kg=HEAVY_LIMIT_KG)
        assert shipping_fee(order) == BASE_FEE

    def test_weight_just_above_heavy_limit_pays_surcharge(self):
        order = make_order(total=10.0, weight_kg=HEAVY_LIMIT_KG + 0.01)
        assert shipping_fee(order) == BASE_FEE + HEAVY_SURCHARGE

    def test_heavy_parcel_pays_base_fee_plus_surcharge(self):
        order = make_order(total=10.0, weight_kg=50.0)
        assert shipping_fee(order) == pytest.approx(BASE_FEE + HEAVY_SURCHARGE)


class TestNegativeWeight:
    def test_negative_weight_raises_value_error(self):
        order = make_order(total=10.0, weight_kg=-0.01)
        with pytest.raises(ValueError):
            shipping_fee(order)

    def test_negative_weight_raises_even_for_member_over_threshold(self):
        order = make_order(total=FREE_SHIPPING_TOTAL, weight_kg=-1.0, member=True)
        with pytest.raises(ValueError):
            shipping_fee(order)

    def test_negative_weight_raises_even_with_promo(self):
        order = make_order(total=0.0, weight_kg=-1.0, promo=True)
        with pytest.raises(ValueError):
            shipping_fee(order)
