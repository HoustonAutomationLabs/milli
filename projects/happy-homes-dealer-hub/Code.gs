/**
 * Happy Homes Dealer Hub — inventory feed
 * -----------------------------------------------------------------------
 * Publishes the "happy homes inventory" spreadsheet as JSON for the
 * dealer portal (index.html).
 *
 * Deploy:  Extensions -> Apps Script -> paste -> Save
 *          Deploy -> Manage deployments -> pencil -> Version: New version
 *          -> Deploy.  Execute as: Me.  Who has access: Anyone.
 *          The /exec URL stays the same across redeploys of the SAME
 *          deployment — do not create a second deployment.
 *
 * Response shape (this is the contract index.html is written against):
 *
 *   {
 *     "generatedAt": "2026-08-25T12:00:00.000Z",
 *     "spreadsheet":  "happy homes inventory",
 *     "categories": [
 *       { "name": "closeout specials",
 *         "count": 48,
 *         "items": [ { "SKU": "...", "Product Name": "...", ... } ] },
 *       ...
 *     ]
 *   }
 *
 * Each item is a plain object keyed by the sheet's own header row, so
 * adding a column to the sheet automatically adds it to the feed.  The
 * portal matches headers case/space-insensitively, so renaming
 * "MSRP" to "Dealer Price" needs no code change here or there.
 *
 * doPost receives order requests forwarded by the Netlify /api/order
 * function and appends one row per line item to the "orders" tab, which is
 * created on first use.  It answers with a reference number the dealer sees
 * on screen.  Requests must carry ORDER_TOKEN; the /exec URL is public, so
 * without that check anyone who found it could append rows.
 */

var SPREADSHEET_ID = '1qaEdVMAqPukhfo13b6CyD2qzoWHdnO-gL2xY-BpjWWc';

/**
 * Orders live in their OWN spreadsheet, not alongside the inventory tabs.
 * Keeping them apart means the orders sheet can be shared, filtered and
 * worked in without exposing the inventory source, and a stray edit while
 * working orders cannot corrupt the catalogue the portal reads.
 */
var ORDERS_SPREADSHEET_ID = '1W9cuKpZjR7eDgU9NJf_isiPDXIm2xgAxWYdMjBOakRE';

/** Tabs to publish, in the order the portal should show them. */
var TAB_NAMES = ['closeout specials', 'sectionals', 'new arrivals'];

/** Cache the assembled payload for this many seconds (0 disables). */
var CACHE_SECONDS = 300;

/** Tab inside the orders spreadsheet. Created on first order. */
var ORDERS_TAB = 'orders';

/** Allowed order statuses. The first is what a new order gets. */
var ORDER_STATUSES = ['New', 'Confirmed', 'Shipped', 'Cancelled'];

/**
 * Shared secret with the Netlify order function. If you change this, change
 * ORDER_TOKEN in netlify/functions/shared.js (or the ORDER_TOKEN environment
 * variable on the Netlify project) to match, then redeploy both.
 */
var ORDER_TOKEN = 'hh-dealer-portal-2026';

var ORDER_HEADERS = ['Order Ref', 'Submitted At', 'Dealer', 'Contact', 'SKU',
                     'Product Name', 'Category', 'Qty', 'Dealer Price',
                     'Line Total', 'Notes', 'Status'];

/** Column index (1-based) of Status, used when updating an order in place. */
var STATUS_COL = 12;

function doGet(e) {
  try {
    var params = (e && e.parameter) || {};

    // The Orders page asks for ?mode=orders. Never cached — someone working
    // orders needs to see a submission the moment it lands.
    if (String(params.mode || '') === 'orders') {
      return json(JSON.stringify(buildOrdersPayload()));
    }

    var fresh = String(params.fresh || '') === '1';
    var cache = CacheService.getScriptCache();
    var cacheKey = 'hh-feed-v2';

    if (!fresh && CACHE_SECONDS > 0) {
      var hit = cache.get(cacheKey);
      if (hit) return json(hit);
    }

    var body = JSON.stringify(buildPayload());

    // CacheService rejects values over 100KB; the full feed is larger than
    // that, so only cache when it fits and just rebuild otherwise.
    if (CACHE_SECONDS > 0 && body.length < 100000) {
      try { cache.put(cacheKey, body, CACHE_SECONDS); } catch (ignore) {}
    }
    return json(body);

  } catch (err) {
    return json(JSON.stringify({
      error: String(err && err.message ? err.message : err),
      categories: []
    }));
  }
}

function buildPayload() {
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var categories = [];

  TAB_NAMES.forEach(function (tabName) {
    var sheet = findSheet(ss, tabName);
    if (!sheet) return;                       // tab renamed or not created yet
    var items = readSheet(sheet);
    categories.push({ name: tabName, count: items.length, items: items });
  });

  return {
    generatedAt: new Date().toISOString(),
    spreadsheet: ss.getName(),
    categories: categories
  };
}

/** Tab lookup that tolerates case and stray whitespace in the tab name. */
function findSheet(ss, wanted) {
  var target = String(wanted).toLowerCase().trim();
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].getName().toLowerCase().trim() === target) return sheets[i];
  }
  return null;
}

/**
 * Read one tab into an array of header-keyed objects.
 * Blank rows and rows with no SKU are skipped, so a trailing blank row
 * in the sheet never becomes a phantom product on the portal.
 */
function readSheet(sheet) {
  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();
  if (lastRow < 2 || lastCol < 1) return [];

  var values = sheet.getRange(1, 1, lastRow, lastCol).getDisplayValues();
  var headers = values[0].map(function (h) { return String(h).trim(); });

  var items = [];
  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    if (!row.join('').trim()) continue;                 // wholly blank row

    var obj = {};
    var hasValue = false;
    for (var c = 0; c < headers.length; c++) {
      if (!headers[c]) continue;                        // unnamed column
      var v = String(row[c] == null ? '' : row[c]).trim();
      obj[headers[c]] = v;
      if (v) hasValue = true;
    }
    // Skip repeated header rows and rows with no identifier at all.
    var sku = String(obj['SKU'] || '').trim();
    if (!hasValue) continue;
    if (sku.toLowerCase() === 'sku') continue;
    if (!sku && !String(obj['Product Name'] || '').trim()) continue;

    items.push(obj);
  }
  return items;
}

function json(body) {
  return ContentService
    .createTextOutput(body)
    .setMimeType(ContentService.MimeType.JSON);
}

/* ===================================================================== *
 * Order intake
 * ===================================================================== */

function doPost(e) {
  try {
    var raw = e && e.postData && e.postData.contents;
    if (!raw) return json(JSON.stringify({ ok: false, error: 'Empty request body' }));

    var payload = JSON.parse(raw);
    if (payload.token !== ORDER_TOKEN) {
      return json(JSON.stringify({ ok: false, error: 'Unauthorized' }));
    }

    if (payload.action === 'setStatus') {
      return json(JSON.stringify(setOrderStatus(payload.reference, payload.status)));
    }

    var items = payload.items;
    if (!items || !items.length) {
      return json(JSON.stringify({ ok: false, error: 'Order contains no items' }));
    }

    var result = appendOrder(payload);
    return json(JSON.stringify({
      ok: true,
      reference: result.reference,
      lines: result.lines,
      total: result.total
    }));

  } catch (err) {
    return json(JSON.stringify({
      ok: false,
      error: String(err && err.message ? err.message : err)
    }));
  }
}

/**
 * Append one row per line item, all sharing an order reference.
 * A script lock serialises reference allocation so two dealers submitting at
 * the same moment cannot be handed the same number.
 */
function appendOrder(payload) {
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var sheet = getOrdersSheet();
    var reference = nextReference();
    var now = new Date();
    var stamp = Utilities.formatDate(now, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
    var total = 0;
    var rows = [];

    for (var i = 0; i < payload.items.length; i++) {
      var it = payload.items[i];
      var qty = Number(it.qty) || 0;
      var price = (it.price === null || it.price === undefined || it.price === '')
        ? '' : Number(it.price);
      var line = (price === '') ? '' : price * qty;
      if (line !== '') total += line;

      rows.push([
        reference, stamp,
        payload.dealer || '', payload.contact || '',
        it.sku || '', it.name || '', it.category || '',
        qty, price, line,
        i === 0 ? (payload.notes || '') : '',
        ORDER_STATUSES[0]
      ]);
    }

    sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, ORDER_HEADERS.length)
         .setValues(rows);

    return { reference: reference, lines: rows.length, total: total };
  } finally {
    lock.releaseLock();
  }
}

/** Return the orders tab, creating it with headers the first time. */
function getOrdersSheet() {
  var ss = SpreadsheetApp.openById(ORDERS_SPREADSHEET_ID);
  var sheet = findSheet(ss, ORDERS_TAB);
  if (!sheet) {
    sheet = ss.insertSheet(ORDERS_TAB);
    sheet.appendRow(ORDER_HEADERS);
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, ORDER_HEADERS.length).setFontWeight('bold');
  } else if (sheet.getLastRow() === 0) {
    sheet.appendRow(ORDER_HEADERS);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

/** Sequential, human-readable reference: HH-20260826-0007 */
function nextReference() {
  var props = PropertiesService.getScriptProperties();
  var n = parseInt(props.getProperty('orderCounter') || '0', 10) + 1;
  props.setProperty('orderCounter', String(n));
  var day = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd');
  var padded = ('0000' + n).slice(-4);
  return 'HH-' + day + '-' + padded;
}

/**
 * Read the orders tab back, grouped one entry per order reference, newest
 * first. This is what the Orders page in Assembly renders.
 */
function buildOrdersPayload() {
  var sheet = getOrdersSheet();
  var lastRow = sheet.getLastRow();
  var orders = [];

  if (lastRow >= 2) {
    var values = sheet.getRange(2, 1, lastRow - 1, ORDER_HEADERS.length).getDisplayValues();
    var byRef = {};

    for (var r = 0; r < values.length; r++) {
      var row = values[r];
      var ref = String(row[0] || '').trim();
      if (!ref) continue;

      if (!byRef[ref]) {
        byRef[ref] = {
          reference: ref,
          submittedAt: row[1] || '',
          dealer: row[2] || '',
          contact: row[3] || '',
          notes: '',
          status: row[11] || ORDER_STATUSES[0],
          items: [],
          lines: 0,
          total: 0
        };
        orders.push(byRef[ref]);
      }
      var order = byRef[ref];
      if (row[10]) order.notes = row[10];

      var qty = Number(row[7]) || 0;
      var price = row[8] === '' ? null : Number(String(row[8]).replace(/[^0-9.\-]/g, ''));
      var line = row[9] === '' ? null : Number(String(row[9]).replace(/[^0-9.\-]/g, ''));

      order.items.push({
        sku: row[4] || '', name: row[5] || '', category: row[6] || '',
        qty: qty, price: isNaN(price) ? null : price,
        lineTotal: isNaN(line) ? null : line
      });
      order.lines += 1;
      if (line && !isNaN(line)) order.total += line;
    }
  }

  orders.reverse();   // newest first; rows are appended chronologically

  return {
    generatedAt: new Date().toISOString(),
    statuses: ORDER_STATUSES,
    count: orders.length,
    orders: orders
  };
}

/**
 * Set the status on every row belonging to one order reference.
 * Returns how many rows changed so a silent no-op cannot pass for success.
 */
function setOrderStatus(reference, status) {
  reference = String(reference || '').trim();
  status = String(status || '').trim();

  if (!reference) return { ok: false, error: 'Missing order reference' };
  if (ORDER_STATUSES.indexOf(status) === -1) {
    return { ok: false, error: 'Unknown status: ' + status };
  }

  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var sheet = getOrdersSheet();
    var lastRow = sheet.getLastRow();
    if (lastRow < 2) return { ok: false, error: 'No orders recorded yet' };

    var refs = sheet.getRange(2, 1, lastRow - 1, 1).getDisplayValues();
    var updated = 0;
    for (var i = 0; i < refs.length; i++) {
      if (String(refs[i][0]).trim() === reference) {
        sheet.getRange(i + 2, STATUS_COL).setValue(status);
        updated += 1;
      }
    }
    if (!updated) return { ok: false, error: 'Order not found: ' + reference };
    return { ok: true, reference: reference, status: status, rowsUpdated: updated };
  } finally {
    lock.releaseLock();
  }
}

/**
 * Run this from the Apps Script editor (Run -> checkOrders) to see what the
 * Orders page will show, without going through Netlify.
 */
function checkOrders() {
  var payload = buildOrdersPayload();
  Logger.log(payload.count + ' order(s) in ' + ORDERS_TAB);
  payload.orders.forEach(function (o) {
    Logger.log('  ' + o.reference + '  ' + o.status + '  ' + o.lines +
               ' line(s)  $' + o.total.toFixed(2) + '  ' + o.dealer);
  });
  return payload.count;
}

/**
 * Run this from the Apps Script editor (Run -> checkOrderIntake) to prove the
 * orders tab and reference counter work, WITHOUT going through Netlify.
 * It writes one test row you should delete afterwards.
 */
function checkOrderIntake() {
  var res = appendOrder({
    dealer: 'TEST — delete this row',
    contact: 'checkOrderIntake',
    notes: 'Written by checkOrderIntake; safe to delete.',
    items: [{ sku: 'TEST-SKU', name: 'Test line item', category: 'Test', qty: 2, price: 9.99 }]
  });
  Logger.log('Wrote ' + res.lines + ' row(s) as ' + res.reference + ', total ' + res.total);
  return res;
}

/**
 * Run this from the Apps Script editor (Run -> checkFeed) after pasting,
 * to confirm every tab is found and the row counts look right BEFORE
 * redeploying. Output appears in the execution log.
 */
function checkFeed() {
  var payload = buildPayload();
  payload.categories.forEach(function (c) {
    Logger.log(c.name + ': ' + c.count + ' rows');
  });
  if (payload.categories.length !== TAB_NAMES.length) {
    Logger.log('WARNING: expected ' + TAB_NAMES.length + ' tabs, found ' +
               payload.categories.length + ' — check TAB_NAMES against the tab names.');
  }
  var first = payload.categories[0] && payload.categories[0].items[0];
  if (first) Logger.log('Columns: ' + Object.keys(first).join(' | '));
  return payload.categories.map(function (c) { return c.name + '=' + c.count; }).join(', ');
}
