/**
 * Local stand-in for Netlify: serves index.html as shipped and routes
 * /api/inventory and /api/order through the REAL function handlers, with the
 * Apps Script call stubbed by a local fixture. Used by run.sh.
 */
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const shared = require(path.join(ROOT, "netlify", "functions", "shared.js"));
const inventory = require(path.join(ROOT, "netlify", "functions", "inventory.js"));
const order = require(path.join(ROOT, "netlify", "functions", "order.js"));
const ordersFn = require(path.join(ROOT, "netlify", "functions", "orders.js"));
const statusFn = require(path.join(ROOT, "netlify", "functions", "order-status.js"));

const FIXTURE = fs.readFileSync(path.join(__dirname, "feed.sample.json"), "utf8");
let counter = 0;

// In-memory stand-in for the orders spreadsheet, so status writes actually
// persist across requests the way Apps Script would.
const STATUSES = ["New", "Confirmed", "Shipped", "Cancelled"];
let ORDERS = [];

// Stand in for the Apps Script deployment: doGet serves inventory or orders,
// doPost submits an order or moves one through the workflow.
global.fetch = async (url, opts) => {
  const base = String(url).split("?")[0];
  if (base !== shared.FEED_URL) throw new Error("unexpected upstream: " + url);
  const wantsOrders = String(url).indexOf("mode=orders") !== -1;

  if (!opts || opts.method !== "POST") {
    if (wantsOrders) {
      return { ok: true, status: 200, text: async () => JSON.stringify({
        generatedAt: new Date().toISOString(),
        statuses: STATUSES,
        count: ORDERS.length,
        orders: ORDERS.slice().reverse(),
      }) };
    }
    return { ok: true, status: 200, text: async () => FIXTURE };
  }

  const body = JSON.parse(opts.body);
  if (body.token !== shared.ORDER_TOKEN) {
    return { ok: true, status: 200, text: async () => JSON.stringify({ ok: false, error: "Unauthorized" }) };
  }

  if (body.action === "setStatus") {
    if (STATUSES.indexOf(body.status) === -1) {
      return { ok: true, status: 200,
        text: async () => JSON.stringify({ ok: false, error: "Unknown status: " + body.status }) };
    }
    const hit = ORDERS.filter((o) => o.reference === body.reference);
    if (!hit.length) {
      return { ok: true, status: 200,
        text: async () => JSON.stringify({ ok: false, error: "Order not found: " + body.reference }) };
    }
    hit.forEach((o) => { o.status = body.status; });
    return { ok: true, status: 200, text: async () => JSON.stringify({
      ok: true, reference: body.reference, status: body.status, rowsUpdated: hit[0].items.length }) };
  }

  counter += 1;
  const reference = "HH-20260826-" + String(counter).padStart(4, "0");
  const items = body.items.map((i) => ({
    sku: i.sku, name: i.name, category: i.category, qty: i.qty,
    price: i.price, lineTotal: i.price == null ? null : i.price * i.qty,
  }));
  const total = items.reduce((n, i) => n + (i.lineTotal || 0), 0);
  ORDERS.push({
    reference,
    submittedAt: new Date().toISOString().slice(0, 19).replace("T", " "),
    dealer: body.dealer, contact: body.contact || "", notes: body.notes || "",
    status: STATUSES[0], items, lines: items.length, total,
  });
  return { ok: true, status: 200,
    text: async () => JSON.stringify({ ok: true, reference, lines: items.length, total }) };
};

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json",
                ".css": "text/css", ".svg": "image/svg+xml" };

http.createServer(async (req, res) => {
  const url = req.url.split("?")[0];

  if (url === "/api/inventory") {
    const out = await inventory.handler({ httpMethod: req.method });
    res.writeHead(out.statusCode, out.headers); return res.end(out.body);
  }

  // Test-only: clear the in-memory orders store so each suite starts clean.
  // Exists solely in this local stand-in; it is not part of the deployed site.
  if (url === "/__reset") {
    ORDERS = [];
    counter = 0;
    res.writeHead(200, { "content-type": "application/json" });
    return res.end(JSON.stringify({ ok: true }));
  }

  if (url === "/api/orders") {
    const out = await ordersFn.handler({ httpMethod: req.method });
    res.writeHead(out.statusCode, out.headers); return res.end(out.body);
  }

  if (url === "/api/order-status") {
    let sbody = "";
    req.on("data", (c) => (sbody += c));
    return req.on("end", async () => {
      const out = await statusFn.handler({ httpMethod: req.method, body: sbody });
      res.writeHead(out.statusCode, out.headers);
      res.end(out.body);
    });
  }

  if (url === "/api/order") {
    let body = "";
    req.on("data", (c) => (body += c));
    return req.on("end", async () => {
      const out = await order.handler({ httpMethod: req.method, body });
      res.writeHead(out.statusCode, out.headers);
      res.end(out.body);
    });
  }

  const file = url === "/" ? "/index.html" : url;
  const full = path.join(ROOT, file);
  if (!full.startsWith(ROOT) || !fs.existsSync(full) || fs.statSync(full).isDirectory()) {
    res.writeHead(404); return res.end("not found");
  }
  res.writeHead(200, { "content-type": TYPES[path.extname(full)] || "application/octet-stream" });
  res.end(fs.readFileSync(full));
}).listen(8899, () => console.log("test server on 8899"));
