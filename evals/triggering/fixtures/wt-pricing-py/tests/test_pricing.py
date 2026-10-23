from pricing import subtotal, shipping, total, tags


def test_subtotal_sums_lines():
    assert subtotal([{"price": 2.50, "qty": 2}, {"price": 1.00, "qty": 3}]) == 8.00


def test_small_order_pays_shipping():
    assert shipping(20.00) == 4.95


def test_total_in_euros():
    assert total([{"price": 10.00, "qty": 1}]) == 14.95


def test_tags():
    lines = [{"price": 1, "qty": 1, "tag": "gift"}, {"price": 1, "qty": 1, "tag": "sale"}, {"price": 1, "qty": 1, "tag": "new"}]
    assert list(tags(lines)) == ["gift", "sale", "new"]
