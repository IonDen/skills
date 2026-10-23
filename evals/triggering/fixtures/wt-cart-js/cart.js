'use strict';

// Cart rules:
// - A line is { price, qty }; the cart total is the sum of price * qty.
// - Tax is added at the rate the tax service returns for the cart's region.
// - Totals are rounded to cents.

function cartTotal(lines, region, taxService) {
  const net = lines.reduce((sum, l) => sum + l.price * l.qty, 0);
  const rate = taxService.rateFor(region);
  return Math.round(net * (1 + rate) * 100) / 100;
}

function orderId() {
  return Math.random().toString(36).slice(2, 10);
}

module.exports = { cartTotal, orderId };
