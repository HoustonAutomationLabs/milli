/**
 * GET /api/orders
 *
 * Returns submitted orders, newest first, for the Orders page embedded in
 * Assembly. Never cached: someone working the queue needs to see a submission
 * the moment it lands.
 */
const { FEED_URL, reply } = require("./shared");

exports.handler = async function (event) {
  const method = (event && event.httpMethod) || "GET";
  if (method !== "GET" && method !== "HEAD") {
    return reply(405, { error: "Method not allowed", orders: [] }, { allow: "GET" });
  }

  try {
    const res = await fetch(FEED_URL + "?mode=orders", { redirect: "follow" });
    if (!res.ok) throw new Error("Orders feed returned HTTP " + res.status);

    const body = await res.text();
    try {
      JSON.parse(body);
    } catch (e) {
      throw new Error("Orders feed did not return JSON (is the web app deployed with access set to Anyone?)");
    }

    return {
      statusCode: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
      },
      body,
    };
  } catch (err) {
    return reply(502, { error: String((err && err.message) || err), orders: [] });
  }
};
