# Happy Homes Dealer Hub — Dealer Home (v5)

Dealer-facing inventory portal for **Happy Homes Industries**, embedded in the
Assembly workspace *Happy Homes Dealer Hub* (`tXaGLcAcp`) and demoed with the
test dealer **On Demand Furniture & Mattress**.

v4 replaced the v3 collapsible category sections with **Meridian-style
horizontal sliders** — one row per category, four cards across on desktop,
arrows and swipe to move along the row. Nothing expands into a wall of cards,
so all three categories stay visible on one screen.

**v5 adds two things:** the inventory feed now runs through a Netlify function,
so the Apps Script URL no longer appears in the page source; and the order
review actually **submits**, writing to an `orders` tab in the sheet and handing
the dealer a reference number.

---

## 1. What changed from v3

| | v3 | v4 |
|---|---|---|
| Category layout | Collapsible banner → wrapping grid of every item | One **horizontal rail** per category, never expands |
| Desktop density | Whole category dumped on screen | 4 cards across, arrows step one page |
| Mobile | 2-col grid, long scroll | 2 cards across, swipe the rail |
| Finding an item | Scroll and hope | Search box + in-stock toggle + 5 sort orders |
| Item detail | Card only | Click the image for a detail panel (dimensions, warehouse, ETA, on-hand) |
| Cart | Drawer + review screen | Same flow, plus quantity capped at units on hand and a copy-paste order text block |
| Order list persistence | Lost on refresh | Kept in the browser (`localStorage`) |
| Categories | Hard-coded to 3 | Driven by the feed; add a sheet tab and a new rail appears |

**Changed in v5: the order review now submits.** It posts to `/api/order`,
which writes to the sheet's `orders` tab and returns a reference number. All
the "nothing is submitted" copy was rewritten to match — a page that says one
thing and does another is worse than either. What it still does *not* do is
notify anyone; see §6.

---

## 2. Architecture

```
Google Sheet "happy homes inventory"   3 inventory tabs + an "orders" tab
        ^                                            |
        | doPost appends order rows                  | doGet serves inventory
        |                                            v
   Apps Script web app  (Code.gs, deployed /exec, access: Anyone)
        ^                                            |
        | POST + shared token                        | JSON
        |                                            v
   Netlify functions   /api/order          /api/inventory
        ^                                            |
        | fetch()                                    | fetch()
        |                                            v
   index.html  (no dependencies, no build step, no CDN)
        |
        |  <iframe>
        v
   Assembly app "Dealer Home"  (embed install 860aec83-…)
```

**The Apps Script URL is never sent to the browser.** It lives only in
`netlify/functions/shared.js`, which executes server-side. The page talks to
`/api/inventory` and `/api/order` on its own domain, so View Source reveals
neither the Google endpoint nor that the data lives in Sheets at all.

Netlify Functions are included on the **free** plan (125k requests/month), so
this costs nothing to run. Note that Netlify's *password protection* is a paid
feature and is not available on free.

### The feed contract

`Code.gs` emits row objects keyed by the sheet's own header row, so **adding a
column to the sheet adds it to the feed automatically**. The portal matches
headers case-, space- and punctuation-insensitively (`MSRP`, `msrp` and
`Dealer Price` all land on the same field), and it also accepts several other
plausible JSON shapes — `{tabs:{…}}`, `{data:[…]}`, or a bare array — so an
older deployed `Code.gs` keeps working until you redeploy.

Column → portal mapping:

| Sheet column | Used for |
|---|---|
| `SKU` | Card label, order list line, dedup key |
| `Product Name` | Card title |
| `Category` | Rail heading when the feed carries no tab name (`Stationary Sectionals` → **Sectionals**) |
| `Collection`, `Color`, `Warehouse` | Card meta line, colour swatch, detail panel |
| `Inventory`, `Status` | Stock badge **and the quantity cap in the order list** |
| `MSRP` | Shown as **Dealer price** |
| `Image URL` | Card image, re-requested at `?width=480` instead of the 2560px original |
| `Description` | Detail panel |
| `ETA` | Shown on sold-out items ("Sold out · ETA 9/7") |
| `Wholesale Price` | Read but not displayed — it is dealer-cost data, deliberately not on a dealer-facing screen |

Rows with no SKU, blank rows and repeated header rows are dropped at both ends.

### Stock badge rules

| Condition | Badge |
|---|---|
| `Status` says sold out / unavailable, or `Inventory` is 0 | **Sold out** (grey), Add disabled, ETA appended if present |
| `Status` says "Last One", or `Inventory` is 1 | **Last one** (red) |
| `Status` says "Low", or `Inventory` ≤ 3 | **Low stock · N left** (amber) |
| anything else | **In stock · N** (green) |

A dealer cannot add more units than `Inventory` — the `+` disables at the cap.

---

## 3. Deploying

### 3a. The site (Netlify)

> **This changed in v5.** The site is no longer a single file — it now ships
> `index.html`, `netlify.toml` and `netlify/functions/`. Drag the **whole
> folder**, not `index.html` on its own, or the two `/api/*` routes 404 and the
> page will show "Could not load live inventory".

The live project is **`dealerhappyhomes`** (`dealerhappyhomes.netlify.app`,
site id `f8cd37c9-2d47-46a1-8051-2db58b38a7ae`). It is a drag-and-drop
project with no connected repo, so deploying means uploading the folder:

1. Open <https://app.netlify.com/projects/dealerhappyhomes>.
2. **Deploys** tab → drag the whole `happy-homes-dealer-hub` folder onto the
   drop zone. Netlify picks up `netlify.toml` and builds the functions.
3. Wait for "Published", then hard-refresh (Ctrl/Cmd-Shift-R). The page
   caches nothing itself, but the browser caches the HTML.

The older `vocal-speculoos-92e013.netlify.app` project from the v3 notes still
exists. Decide which one is canonical and point Assembly at that one only —
two live copies drifting apart is how the wrong prices get quoted.

### 3b. The feed (Apps Script)

1. Open the sheet → **Extensions → Apps Script**.
2. Select all in `Code.gs`, delete, paste this repo's `Code.gs`, **Save**.
3. **Run → `checkFeed`** first. The execution log should read:
   `closeout specials: 48 rows` / `sectionals: 15 rows` / `new arrivals: 15 rows`.
   If a tab reports 0 or is missing, `TAB_NAMES` no longer matches the tab names —
   fix that before deploying.
4. **Deploy → Manage deployments → pencil → Version: New version → Deploy.**
5. Confirm the `/exec` URL is unchanged. It is, as long as you edited the
   existing deployment rather than creating a new one.

If you ever need to bypass the 5-minute cache, add `?fresh=1` to the `/exec` URL.

**Order intake.** `doPost` in the same script receives orders forwarded by
`/api/order` and appends one row per line item to an **`orders`** tab, created
automatically on the first submission. Columns:

```
Order Ref | Submitted At | Dealer | Contact | SKU | Product Name |
Category | Qty | Dealer Price | Line Total | Notes
```

References are sequential and human-readable — `HH-20260826-0001` — allocated
under a script lock so two dealers submitting at once cannot collide.

To prove intake works without going through Netlify, **Run → `checkOrderIntake`**
in the Apps Script editor. It writes one clearly-labelled test row; delete it
afterwards.

**The shared token.** `/exec` is world-readable, so `doPost` requires a token
that only the Netlify function knows. It is `ORDER_TOKEN` in both
`Code.gs` and `netlify/functions/shared.js` — if you change one, change the
other and redeploy both, or every order will come back "Unauthorized".

### 3c. The Assembly embed

Dealer Home is already an **embed**-type app install in the workspace, so this
is a URL change, not a new install:

1. Assembly dashboard → **Apps** → **Dealer Home** → edit.
2. Set the embed URL to `https://dealerhappyhomes.netlify.app/`.
3. **Turn auto-size off / give the iframe a fixed height** (≥ 720px; 900px is
   comfortable). The portal is built as a fixed-height app with its own
   internal scrolling — that is what keeps the sticky header, the cart drawer
   and the modals anchored correctly. In an auto-sized iframe they would
   anchor to a very tall viewport and drift off-screen.

The page also posts its height to the parent frame on load and resize, so if
Assembly's auto-size listens for a `{type:'resize', height}` message it will
still fit.

---

## 4. Configuring the portal

Everything adjustable sits in one `CONFIG` block near the top of the `<script>`
in `index.html`:

```js
var CONFIG = {
  feedUrl:        "/api/inventory",   // Netlify function, not the Google URL
  orderUrl:       "/api/order",
  dealerName:     "On Demand Furniture & Mattress",
  dealerContact:  "",
  categoryOrder:  ["Closeout Specials", "Sectionals", "New Arrivals"],
  categoryAliases:{ "stationary sectionals": "Sectionals" },
  thumbWidth:     480,
  cartThumbWidth: 120,
  storageKey:     "hh-dealer-order-list-v1"
};
```

- **Reorder the rows** — reorder `categoryOrder`.
- **Add a category** — add a tab to the sheet, add its name to `TAB_NAMES` in
  `Code.gs`, redeploy. A new rail appears; add it to `categoryOrder` to place it.
- **Per-dealer branding** — change `dealerName`. (See §6 for doing this properly.)

---

## 5. What was verified

Run against a local mock of the feed built from real sheet rows, using
Chromium via Playwright.

**Data layer — 24 checks** (`normalizeFeed`, `stock`, price/image parsing):
all four accepted JSON shapes group correctly; `Stationary Sectionals` aliases
to `Sectionals`; header and blank rows are dropped; `"$499.99"` parses while a
blank MSRP stays `null` rather than becoming `$0.00`; the two different
products both called `310-04` stay separate order lines; `http://` image URLs
are upgraded to `https` and an existing `?width=2560` is replaced, not appended.

**Netlify functions — 27 checks**: method rejection, malformed and oversized
bodies, the 200-line cap, and the error paths (upstream 500, upstream returning
Google's sign-in HTML instead of JSON, a thrown fetch). On the happy path it
asserts what actually reaches Apps Script: the shared token is injected
server-side and **a caller-supplied `token` cannot override it**, a string qty
is coerced to a number, a negative qty clamps to 1, an over-long SKU truncates,
and a null price stays null rather than becoming `0`.

**Browser — 49 checks**: exactly 4 cards across at 1440px and 2 at 390px;
12 closeout cards sit on **one row** (measured — this is the "does not expand"
requirement); arrows appear/hide at the ends and move the rail; sold-out cards
are disabled and show "Call for dealer price" where no price exists; add →
stepper → cart total → review → print flow; Escape closes; search, in-stock
filter and price sort; the order list survives a page reload; no uncaught JS
errors. Plus, for v5: the page source contains **no** `script.google.com` and
no `AKfycb…` deployment id; a submitted order returns a reference, shows the
confirmation and clears the order list; and a **failed** submission shows an
error, keeps the order list intact, and re-enables the button for a retry.

The browser suite runs against `test/serve.js`, which executes the **real**
function handlers with only the Apps Script call stubbed — so the page under
test is byte-for-byte the one that ships.

Run them yourself:

```bash
cd projects/happy-homes-dealer-hub/test
./run.sh          # data suite, then the browser suite against a local fixture
```

`run.sh` extracts the data layer out of `index.html`, serves a copy of the page
pointed at `feed.sample.json`, and drives it with Chromium. It needs `node`,
`python3` and `playwright` with a Chromium build; it exits non-zero if any
check fails and writes screenshots next to the tests.

One real bug was found and fixed this way: the cart drawer sits off-screen at
`translateX(101%)`, and because `#app` was not a positioned ancestor the drawer
anchored to the viewport instead — adding **424px of horizontal scroll to the
whole page, on desktop as well as mobile**. `#app` now has `position:relative`.

**Not verified here:** the live `/exec` feed and the deployed site. This
sandbox's network blocks `script.google.com` and `*.netlify.app`, so the real
feed response was never fetched. The sheet itself was read directly (via Drive)
and the parser was tested against rows taken from it. Product images likewise
could not load in-sandbox, which is why the screenshots show the "No image"
placeholder — that placeholder is also the genuine fallback for a dead image URL.

---

## 6. Open items

- **All Inventory/Status values across all three tabs are example data**, not a
  live warehouse feed. The portal says so on the page. Replace with a real feed
  before any dealer treats these counts as bookable.
- **Every dealer currently sees the same `dealerName`.** It is a constant in the
  HTML, so "signed in as On Demand Furniture & Mattress" is hard-coded. Assembly
  can pass the viewing client through — that is the next step for a multi-dealer
  demo (see below).
- **Orders are recorded, not announced.** A submission lands in the sheet's
  `orders` tab. Nobody is emailed. Add a notification (Make watching the tab, or
  `MailApp` in `doPost`) before a real dealer relies on it, or orders will sit
  unseen.
- **The dealer identity is still a constant.** Every submission is stamped
  `On Demand Furniture & Mattress` from `CONFIG.dealerName`, so with more than
  one dealer the `orders` tab cannot tell them apart. Passing the signed-in
  Assembly client through to the embed fixes this and is the prerequisite for
  a multi-dealer demo.
- **The shared token is a demo-grade control.** It stops drive-by writes to the
  `orders` tab; it is not authentication. It never reaches the browser, but it
  is checked into this repo — set `ORDER_TOKEN` as a Netlify environment
  variable and change it in `Code.gs` before this handles anything real.
- The three $9.99 rows (4-digit retail codes: A8010236, T037-13, A2000678) and
  the two SKU/name mismatches (Franklin 893-10 / 893-22, Franklin 713 / 840) are
  still flagged in the Description column and unresolved. They are visible to
  dealers as real prices right now.
- Poland Black has no dealer price; it renders as "Call for dealer price".
- Two Netlify projects (`dealerhappyhomes`, `vocal-speculoos-92e013`) are both
  live. Retire one.

### Suggested next phases for Assembly

The workspace already has the right pieces installed — Dealer Home and
Inventory - HQ (embeds), Messages, Forms, and a custom Order Tracker.

1. **Identify the dealer.** Assembly can pass the signed-in client's identity to
   an embed. Reading it lets the portal greet the right dealer and, later, show
   dealer-specific pricing tiers.
2. **Turn "Review order selections" into a real submission.** Post the order
   list to a Make webhook → append to an `orders` tab → notify Happy Homes.
   The Order Tracker app then shows the dealer their own order status.
3. **Back-in-stock interest.** Sold-out items are the most useful signal you
   have: a "notify me" button on a sold-out card tells Happy Homes what demand
   they are missing. That is the argument that makes them want the portal.
4. **Real inventory.** Everything above is worth more once the counts are live.
