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

const FIXTURE = fs.readFileSync(path.join(__dirname, "feed.sample.json"), "utf8");
let counter = 0;

// Stand in for the Apps Script deployment: GET returns the fixture,
// POST behaves like doPost in Code.gs.
global.fetch = async (url, opts) => {
  if (url !== shared.FEED_URL) throw new Error("unexpected upstream: " + url);
  if (!opts || opts.method !== "POST") {
    return { ok: true, status: 200, text: async () => FIXTURE };
  }
  const body = JSON.parse(opts.body);
  if (body.token !== shared.ORDER_TOKEN) {
    return { ok: true, status: 200, text: async () => JSON.stringify({ ok: false, error: "Unauthorized" }) };
  }
  counter += 1;
  const total = body.items.reduce((n, i) => n + (i.price || 0) * i.qty, 0);
  return {
    ok: true, status: 200,
    text: async () => JSON.stringify({
      ok: true,
      reference: "HH-20260826-" + String(counter).padStart(4, "0"),
      lines: body.items.length,
      total,
    }),
  };
};

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json",
                ".css": "text/css", ".svg": "image/svg+xml" };

http.createServer(async (req, res) => {
  const url = req.url.split("?")[0];

  if (url === "/api/inventory") {
    const out = await inventory.handler({ httpMethod: req.method });
    res.writeHead(out.statusCode, out.headers); return res.end(out.body);
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
