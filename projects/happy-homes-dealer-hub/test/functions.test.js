/**
 * Unit tests for the Netlify functions. The upstream Apps Script call is
 * stubbed, so these assert our own validation, normalisation and error paths.
 */
const path = require("path");
const shared = require(path.join(__dirname, "..", "netlify", "functions", "shared.js"));
const inventory = require(path.join(__dirname, "..", "netlify", "functions", "inventory.js"));
const order = require(path.join(__dirname, "..", "netlify", "functions", "order.js"));

let pass = 0, fail = 0;
const ok = (n, c, x) => { if (c) { pass++; console.log("  ok  " + n); }
                          else { fail++; console.log("  FAIL " + n + (x !== undefined ? "  -> " + x : "")); } };

const realFetch = global.fetch;
let lastCall = null;
function stub(impl) { global.fetch = async (url, opts) => { lastCall = { url, opts }; return impl(url, opts); }; }
const res = (body, okFlag = true, status = 200) => ({
  ok: okFlag, status, text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
});

(async () => {
  console.log("\ninventory function");

  stub(() => res({ categories: [{ name: "sectionals", items: [{ SKU: "X" }] }] }));
  let r = await inventory.handler({ httpMethod: "GET" });
  ok("200 on a good feed", r.statusCode === 200, r.statusCode);
  ok("passes the feed body through untouched",
     JSON.parse(r.body).categories[0].items[0].SKU === "X");
  ok("sets a cache header", /max-age/.test(r.headers["cache-control"] || ""));
  ok("calls the Apps Script URL", lastCall.url === shared.FEED_URL);

  r = await inventory.handler({ httpMethod: "POST" });
  ok("405 on POST", r.statusCode === 405, r.statusCode);

  stub(() => res("<!DOCTYPE html><html>Google sign-in</html>"));
  r = await inventory.handler({ httpMethod: "GET" });
  ok("502 when the feed returns HTML instead of JSON", r.statusCode === 502, r.statusCode);
  ok("error names the likely cause (access not set to Anyone)",
     /Anyone/.test(JSON.parse(r.body).error), JSON.parse(r.body).error);
  ok("still returns an empty categories array so the page can render",
     Array.isArray(JSON.parse(r.body).categories));

  stub(() => res("", false, 500));
  r = await inventory.handler({ httpMethod: "GET" });
  ok("502 when upstream 500s", r.statusCode === 502, r.statusCode);

  stub(() => { throw new Error("network down"); });
  r = await inventory.handler({ httpMethod: "GET" });
  ok("502 when the fetch throws", r.statusCode === 502 && /network down/.test(JSON.parse(r.body).error));

  console.log("\norder function — rejections");

  r = await order.handler({ httpMethod: "GET" });
  ok("405 on GET", r.statusCode === 405, r.statusCode);

  r = await order.handler({ httpMethod: "POST", body: "not json" });
  ok("400 on malformed JSON", r.statusCode === 400, r.statusCode);

  r = await order.handler({ httpMethod: "POST", body: JSON.stringify({ items: [] }) });
  ok("400 on an empty order", r.statusCode === 400 && /no items/i.test(JSON.parse(r.body).error));

  r = await order.handler({ httpMethod: "POST",
    body: JSON.stringify({ items: new Array(201).fill({ sku: "A", qty: 1 }) }) });
  ok("400 over the 200-line cap", r.statusCode === 400 && /200 line/.test(JSON.parse(r.body).error));

  r = await order.handler({ httpMethod: "POST", body: "x".repeat(300 * 1024) });
  ok("413 on an oversized body", r.statusCode === 413, r.statusCode);

  console.log("\norder function — the happy path and what it forwards");

  stub(() => res({ ok: true, reference: "HH-20260826-0001", lines: 2, total: 1099.97 }));
  r = await order.handler({ httpMethod: "POST", body: JSON.stringify({
    dealer: "On Demand Furniture & Mattress",
    notes: "PO 12345",
    items: [
      { sku: "Rocket Onyx", name: "Rocket Onyx Sectional", category: "Sectionals", qty: 2, price: 369.99 },
      { sku: "POLAND BLACK", name: "Poland Black", category: "Sectionals", qty: "3", price: null }
    ]
  }) });
  ok("200 on success", r.statusCode === 200, r.statusCode);
  const body = JSON.parse(r.body);
  ok("returns the reference to the page", body.reference === "HH-20260826-0001", body.reference);

  const sent = JSON.parse(lastCall.opts.body);
  ok("POSTs to the Apps Script URL", lastCall.url === shared.FEED_URL && lastCall.opts.method === "POST");
  ok("injects the shared token server-side", sent.token === shared.ORDER_TOKEN);
  ok("token is NOT something the caller can set",
     JSON.parse((await order.handler({ httpMethod: "POST", body: JSON.stringify({
       token: "attacker-supplied", items: [{ sku: "A", qty: 1 }] }) })).statusCode === 200
       ? lastCall.opts.body : lastCall.opts.body).token === shared.ORDER_TOKEN);
  ok("coerces a string qty to a number", sent.items[1].qty === 3, sent.items[1].qty);
  ok("keeps a null price null rather than inventing 0", sent.items[1].price === null, sent.items[1].price);
  ok("carries the dealer and notes through", sent.dealer.indexOf("On Demand") === 0 && sent.notes === "PO 12345");

  stub(() => res({ ok: true }));
  r = await order.handler({ httpMethod: "POST",
    body: JSON.stringify({ items: [{ sku: "A", qty: -5, price: 10 }] }) });
  ok("clamps a negative qty up to 1", JSON.parse(lastCall.opts.body).items[0].qty === 1);

  r = await order.handler({ httpMethod: "POST",
    body: JSON.stringify({ items: [{ sku: "A".repeat(500), qty: 1 }] }) });
  ok("truncates an over-long SKU", JSON.parse(lastCall.opts.body).items[0].sku.length === 120);

  console.log("\norder function — upstream failures");

  stub(() => res({ ok: false, error: "Unauthorized" }));
  r = await order.handler({ httpMethod: "POST", body: JSON.stringify({ items: [{ sku: "A", qty: 1 }] }) });
  ok("502 and surfaces the reason when Apps Script rejects",
     r.statusCode === 502 && /Unauthorized/.test(JSON.parse(r.body).error));

  stub(() => res("<html>error</html>"));
  r = await order.handler({ httpMethod: "POST", body: JSON.stringify({ items: [{ sku: "A", qty: 1 }] }) });
  ok("502 when Apps Script returns non-JSON", r.statusCode === 502, r.statusCode);

  global.fetch = realFetch;
  console.log("\n" + pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})();
