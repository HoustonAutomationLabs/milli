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
 */

var SPREADSHEET_ID = '1qaEdVMAqPukhfo13b6CyD2qzoWHdnO-gL2xY-BpjWWc';

/** Tabs to publish, in the order the portal should show them. */
var TAB_NAMES = ['closeout specials', 'sectionals', 'new arrivals'];

/** Cache the assembled payload for this many seconds (0 disables). */
var CACHE_SECONDS = 300;

function doGet(e) {
  try {
    var params = (e && e.parameter) || {};
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
