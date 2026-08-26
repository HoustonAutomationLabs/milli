/**
 * Shared config for the two dealer-hub functions.
 *
 * FEED_URL is read from a Netlify environment variable when one is set, and
 * otherwise falls back to the value below. Either way it stays server-side:
 * function code is executed on Netlify, never shipped to the browser.
 *
 * To rotate the Apps Script deployment without touching code, set FEED_URL
 * in Netlify → Project configuration → Environment variables.
 */
const FEED_URL =
  process.env.FEED_URL ||
  "https://script.google.com/macros/s/AKfycbxYZ01poWvj6iCN18XnJ1P7GhbyfuCTzJzmqEkvwgPakHYm8H8-a0gFaNZcjBpI1XZ5Cw/exec";

/**
 * Shared secret between this function and doPost in Code.gs. The /exec URL is
 * world-readable, so without this anyone who found it could append junk rows
 * to the orders tab. Override with an ORDER_TOKEN environment variable and
 * change ORDER_TOKEN in Code.gs to match.
 */
const ORDER_TOKEN = process.env.ORDER_TOKEN || "hh-dealer-portal-2026";

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "x-content-type-options": "nosniff",
};

function reply(statusCode, obj, extraHeaders) {
  return {
    statusCode,
    headers: Object.assign({}, JSON_HEADERS, extraHeaders || {}),
    body: JSON.stringify(obj),
  };
}

module.exports = { FEED_URL, ORDER_TOKEN, JSON_HEADERS, reply };
