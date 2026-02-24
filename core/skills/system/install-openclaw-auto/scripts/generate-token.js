#!/usr/bin/env node
// Generate random token for gateway auth

const crypto = require('crypto');

function generateToken(length = 48) {
  return crypto.randomBytes(length).toString('hex');
}

console.log(generateToken());
