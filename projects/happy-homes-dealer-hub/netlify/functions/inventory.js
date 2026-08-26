/**
 * GET /api/inventory
 *
 * Server-side proxy for the Apps Script inventory feed. The browser only ever
 * sees a same-origin URL, so the Google endpoint (and the fact that the data
 * lives in Sheets at all) stays out of the page source.
 */
const { FEED_URL, reply } = require("./shared");

exports.handler = async function (event) {
  const method = (event && event.httpMethod) || "GET";
  if (method !== "GET" && method !== "HEAD") {
    return reply(405, { error: "Method not allowed", categories: [] }, { allow: "GET" });
  }

  try {
    const res = await fetch(FEED_URL, { redirect: "follow" });
    if (!res.ok) throw new Error("Feed returned HTTP " + res.status);

    const body = await res.text();

    // Fail loudly here rather than handing the page something it cannot parse.
    try {
      JSON.parse(body);
    } catch (e) {
      throw new Error("Feed did not return JSON (is the web app deployed with access set to Anyone?)");
    }

    return {
      statusCode: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        // Short shared cache: the sheet changes rarely and this keeps the
        // Apps Script quota well clear of the free-plan limits.
        "cache-control": "public, max-age=120, stale-while-revalidate=600",
      },
      body,
    };
  } catch (err) {
    return reply(502, {
      error: String((err && err.message) || err),
      categories: [],
    });
  }
};
