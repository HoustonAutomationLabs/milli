/**
 * POST /api/order-status   { reference, status }
 *
 * Moves one order through the workflow. The shared token is added here so it
 * never reaches the browser, and the status is checked against the allowed
 * list on both sides — this endpoint is public, and the sheet should not
 * accept an arbitrary string as a status.
 */
const { FEED_URL, ORDER_TOKEN, reply } = require("./shared");

const ALLOWED = ["New", "Confirmed", "Shipped", "Cancelled"];

exports.handler = async function (event) {
  if (!event || event.httpMethod !== "POST") {
    return reply(405, { ok: false, error: "Method not allowed" }, { allow: "POST" });
  }

  let payload;
  try {
    payload = JSON.parse(event.body || "{}");
  } catch (e) {
    return reply(400, { ok: false, error: "Malformed request body" });
  }

  const reference = String((payload && payload.reference) || "").trim().slice(0, 64);
  const status = String((payload && payload.status) || "").trim();

  if (!reference) return reply(400, { ok: false, error: "Missing order reference" });
  if (ALLOWED.indexOf(status) === -1) {
    return reply(400, { ok: false, error: "Status must be one of: " + ALLOWED.join(", ") });
  }

  try {
    const res = await fetch(FEED_URL, {
      method: "POST",
      redirect: "follow",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        token: ORDER_TOKEN,
        action: "setStatus",
        reference,
        status,
      }),
    });

    const text = await res.text();
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      throw new Error("Status endpoint did not return JSON");
    }
    if (!res.ok || !parsed.ok) {
      throw new Error(parsed.error || "Status update was rejected");
    }

    return reply(200, {
      ok: true,
      reference: parsed.reference,
      status: parsed.status,
      rowsUpdated: parsed.rowsUpdated,
    });
  } catch (err) {
    return reply(502, { ok: false, error: String((err && err.message) || err) });
  }
};
