'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { cartTotal, orderId } = require('../cart');
const taxService = require('../taxService');

test('cart total includes tax', () => {
  assert.strictEqual(cartTotal([{ price: 10, qty: 2 }], 'NL', taxService), 24.2);
});

test('order ids are 8 characters', () => {
  assert.strictEqual(orderId().length, 8);
});
