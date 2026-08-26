/**
 * POST /api/order
 *
 * Accepts an order request from the dealer portal, validates it, and forwards
 * it to doPost in Code.gs, which appends one row per line item to the sheet's
 * "orders" tab and returns a reference number.
 *
 * The shared token is added here, server-side, so it never reaches the browser.
 */
const { FEED_URL, ORDER_TOKEN, reply } = require("./shared");

const MAX_LINES = 200;
const MAX_BODY_BYTES = 256 * 1024;

exports.handler = async function (event) {
  if (!event || event.httpMethod !== "POST") {
    return reply(405, { ok: false, error: "Method not allowed" }, { allow: "POST" });
  }

  const raw = event.body || "";
  if (Buffer.byteLength(raw, "utf8") > MAX_BODY_BYTES) {
    return reply(413, { ok: false, error: "Order is too large" });
  }

  let payload;
  try {
    payload = JSON.parse(raw);
  } catch (e) {
    return reply(400, { ok: false, error: "Malformed request body" });
  }

  const items = Array.isArray(payload && payload.items) ? payload.items : [];
  if (!items.length) return reply(400, { ok: false, error: "Order contains no items" });
  if (items.length > MAX_LINES) {
    return reply(400, { ok: false, error: "Order exceeds " + MAX_LINES + " line items" });
  }

  // Normalise here so the sheet never receives arbitrary client-supplied shapes.
  const clean = items.map(function (it) {
    const qty = Math.max(1, Math.min(9999, parseInt(it && it.qty, 10) || 1));
    const price = it && it.price != null && isFinite(it.price) ? Number(it.price) : null;
    return {
      sku: String((it && it.sku) || "").slice(0, 120),
      name: String((it && it.name) || "").slice(0, 300),
      category: String((it && it.category) || "").slice(0, 120),
      qty,
      price,
    };
  });

  const body = {
    token: ORDER_TOKEN,
    dealer: String((payload && payload.dealer) || "").slice(0, 200),
    contact: String((payload && payload.contact) || "").slice(0, 200),
    notes: String((payload && payload.notes) || "").slice(0, 2000),
    items: clean,
  };

  try {
    const res = await fetch(FEED_URL, {
      method: "POST",
      redirect: "follow",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });

    const text = await res.text();
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      throw new Error("Order endpoint did not return JSON");
    }
    if (!res.ok || !parsed.ok) {
      throw new Error(parsed.error || "Order endpoint rejected the request");
    }

    return reply(200, {
      ok: true,
      reference: parsed.reference,
      lines: parsed.lines,
      total: parsed.total,
    });
  } catch (err) {
    return reply(502, { ok: false, error: String((err && err.message) || err) });
  }
};
