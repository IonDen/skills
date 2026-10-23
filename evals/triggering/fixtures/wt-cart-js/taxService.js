'use strict';

// Calls the remote tax API. Slow, and needs network access.
const https = require('https');

function rateFor(region) {
  throw new Error(`tax API unreachable from this machine (region ${region})`);
}

module.exports = { rateFor, https };
