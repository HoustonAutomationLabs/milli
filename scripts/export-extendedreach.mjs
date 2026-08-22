#!/usr/bin/env node
/**
 * ExtendedReach report exporter.
 *
 * ExtendedReach has no report-level scheduling and no API on the agency's plan
 * (see docs/extendedreach-audit.md). Every report does, however, offer a
 * one-click Excel export. This script drives a real browser session to click
 * those exports on a schedule, dropping the workbooks into a directory the
 * dashboard's `exports` data source reads.
 *
 * It is deliberately boring automation of an authorised, manual task: sign in
 * as a real user, open each report, click Excel. It does not scrape rendered
 * rows, bypass any control, or touch anything outside the Reports area.
 *
 * MFA
 * ---
 * Most tenants require MFA, which cannot (and should not) be automated. The
 * first run is interactive: you sign in and complete MFA yourself, and the
 * authenticated session is saved to disk. Later runs reuse it, unattended,
 * until it expires — then you re-run with --login once.
 *
 *   node scripts/export-extendedreach.mjs --login     # interactive, saves session
 *   node scripts/export-extendedreach.mjs             # unattended, uses session
 *   node scripts/export-extendedreach.mjs --only pastdue_case
 *
 * Never commit the session file or credentials. Both are gitignored.
 */

import { chromium } from "playwright";
import { mkdir, writeFile, access } from "node:fs/promises";
import { constants } from "node:fs";
import path from "node:path";
import process from "node:process";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL = process.env.ER_BASE_URL ?? "";
const USERNAME = process.env.ER_USERNAME ?? "";
const PASSWORD = process.env.ER_PASSWORD ?? "";
const OUT_DIR = process.env.ER_EXPORT_DIR ?? "./data/exports";
const STATE_FILE = process.env.ER_SESSION_FILE ?? "./.er-session.json";
const NAV_TIMEOUT = Number(process.env.ER_NAV_TIMEOUT_MS ?? 45_000);

/**
 * The reports the dashboard depends on, keyed by the slug used in filenames.
 * `view` is ExtendedReach's internal view code, confirmed during the audit.
 *
 * TODO(phase-2): confirm the URL pattern for a view code. The audit recorded
 * the codes but not the address they resolve to. Open one report in the UI,
 * copy the URL, and set ER_REPORT_URL_TEMPLATE (e.g. "/reports/view?id={view}").
 * Until then the script falls back to menu navigation via `menuPath`.
 */
const REPORTS = [
  { slug: "pastdue_case",  view: "V_TASKS_INPROC_PASTDUEBYDATE-C",      menuPath: ["Cases", "Case Tasks", "Due Soon/Past Due"] },
  { slug: "pastdue_home",  view: "V_HOMETASKS_INPROC_PASTDUEBYDATE-C",  menuPath: ["Homes", "Home Tasks", "Due Soon/Past Due"] },
  { slug: "inprocess",     view: "V_TASKS_INPROC-C",                    menuPath: ["Cases", "Case Tasks", "In Process"] },
  { slug: "completions",   view: "V_ALLBYCOMPLETION_ACTIVITIES-C",      menuPath: ["Summaries", "Casework", "Activities Completed by Date"] },
  { slug: "caseload",      view: "V_CASELOADS_WKR_MONTH-C",             menuPath: ["Cases", "Case Rosters", "Monthly Census by Worker"] },
  { slug: "ontime",        view: "V_MONTHVAR-C",                        menuPath: ["Summaries", "Casework", "% On Time by Program"] },
  { slug: "opencases",     view: "V_CLIENTS_LASTNAME_ACTIVE-C",         menuPath: ["Cases", "Case Rosters", "Foster Care Open Cases"] },
  { slug: "openbeds",      view: "V_HOMES_AVAILABLE-C",                 menuPath: ["Homes", "Home Rosters", "Open Beds"] },
  { slug: "nextcourt",     view: "V_CLIENTS_NEXTCOURT-C",               menuPath: ["Cases", "Case Rosters", "Next Court Date"] },
  { slug: "staffexp",      view: "V_STAFF_EXPBYDATE-C",                 menuPath: ["Summaries", "Staff", "Events + Expirations"] },
  // Verified against real exports 2026-08-22; see src/lib/extendedreach/schema.ts.
  { slug: "needapproval_case", view: "V_REPORTS_NEEDAPPROVAL-C",        menuPath: ["Cases", "Case Tasks", "Awaiting Approval"] },
  { slug: "rejected_case",     view: "V_TASKS_REJECTED-C",              menuPath: ["Cases", "Case Tasks", "Rejected"] },
  { slug: "reportscompleted",  view: "V_ALLBYCOMPLETION_REPORTS-C",     menuPath: ["Summaries", "Casework", "Reports Completed by Date"] },
  // A custom report, not a view: it has no view code and is reached by name.
  // It also downloads as CSV rather than Excel, which `downloadReport` must
  // allow for — see the extension note there.
  { slug: "compliance_case",   view: "A_COMPLIANCE_CASES",              menuPath: ["Cases", "Case Tasks", "Compliance Tracking"] },
];

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

const args = process.argv.slice(2);
const flag = (n) => args.includes(`--${n}`);
const opt = (n) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : undefined; };

const stamp = () => new Date().toISOString().slice(0, 10).replace(/-/g, "");
const log = (...m) => console.log(`[${new Date().toISOString().slice(11, 19)}]`, ...m);
const fail = (msg) => { console.error(`\n✖ ${msg}\n`); process.exit(1); };

async function exists(p) {
  try { await access(p, constants.R_OK); return true; } catch { return false; }
}

// ---------------------------------------------------------------------------
// Sign-in
// ---------------------------------------------------------------------------

/**
 * Interactive sign-in. Opens a headed browser, fills what it can, and waits
 * for you to finish MFA. Saves the authenticated session for later runs.
 */
async function interactiveLogin() {
  if (!BASE_URL) fail("ER_BASE_URL is not set. See .env.example.");

  log("Opening a browser for interactive sign-in…");
  const browser = await chromium.launch({ headless: false });
  const ctx = await browser.newContext({ acceptDownloads: true });
  const page = await ctx.newPage();
  page.setDefaultTimeout(NAV_TIMEOUT);

  await page.goto(BASE_URL);

  // Best-effort prefill; the operator completes whatever remains, incl. MFA.
  if (USERNAME) {
    const user = page.locator('input[type="email"], input[name*="user" i], input[id*="user" i]').first();
    if (await user.count()) await user.fill(USERNAME).catch(() => {});
  }
  if (PASSWORD) {
    const pass = page.locator('input[type="password"]').first();
    if (await pass.count()) await pass.fill(PASSWORD).catch(() => {});
  }

  console.log("\n  → Complete sign-in and MFA in the browser window.");
  console.log("  → Once you can see the ExtendedReach home page, press Enter here.\n");
  await new Promise((r) => process.stdin.once("data", r));

  await ctx.storageState({ path: STATE_FILE });
  log(`Session saved to ${STATE_FILE}`);
  await browser.close();
}

// ---------------------------------------------------------------------------
// Export a single report
// ---------------------------------------------------------------------------

/**
 * Navigate to one report and click its Excel button, returning the saved path.
 * Prefers a direct URL when ER_REPORT_URL_TEMPLATE is configured; otherwise
 * walks the menu by visible link text.
 */
async function exportReport(page, report, outDir) {
  const tmpl = process.env.ER_REPORT_URL_TEMPLATE;

  if (tmpl) {
    const url = new URL(tmpl.replace("{view}", encodeURIComponent(report.view)), BASE_URL).toString();
    await page.goto(url, { waitUntil: "domcontentloaded" });
  } else {
    await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
    for (const step of report.menuPath) {
      const link = page.getByRole("link", { name: step, exact: false }).first();
      await link.waitFor({ state: "visible" });
      await link.click();
      await page.waitForLoadState("domcontentloaded");
    }
  }

  // The toolbar exposes the export as a link or button labelled "Excel".
  const excel = page
    .getByRole("link", { name: /excel/i })
    .or(page.getByRole("button", { name: /excel/i }))
    .first();

  await excel.waitFor({ state: "visible" });

  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: NAV_TIMEOUT }),
    excel.click(),
  ]);

  // Do not assume the extension. The report views export Excel, but the
  // Compliance Tracking custom reports download as CSV even though the control
  // is still labelled "Excel". Naming a CSV `.xlsx` would make the loader hand
  // it to the workbook parser, which fails with no useful message.
  const suggested = download.suggestedFilename() ?? "";
  const ext = /\.(xlsx|csv)$/i.exec(suggested)?.[1].toLowerCase() ?? "xlsx";
  const dest = path.join(outDir, `${report.slug}_${stamp()}.${ext}`);
  await download.saveAs(dest);
  return dest;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  if (flag("login")) return interactiveLogin();

  if (!BASE_URL) fail("ER_BASE_URL is not set. See .env.example.");
  if (!(await exists(STATE_FILE))) {
    fail(
      `No saved session at ${STATE_FILE}.\n` +
      `  Run once interactively first:  node scripts/export-extendedreach.mjs --login`,
    );
  }

  const only = opt("only");
  const targets = only ? REPORTS.filter((r) => r.slug === only) : REPORTS;
  if (!targets.length) fail(`No report matches --only ${only}`);

  const outDir = path.resolve(OUT_DIR);
  await mkdir(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: !flag("headed") });
  const ctx = await browser.newContext({ storageState: STATE_FILE, acceptDownloads: true });
  const page = await ctx.newPage();
  page.setDefaultTimeout(NAV_TIMEOUT);

  const results = [];
  for (const report of targets) {
    try {
      log(`↓ ${report.slug} …`);
      const file = await exportReport(page, report, outDir);
      log(`  saved ${path.basename(file)}`);
      results.push({ slug: report.slug, view: report.view, status: "ok", file });
    } catch (err) {
      // One failed report must not lose the others.
      console.error(`  ✖ ${report.slug}: ${err.message}`);
      results.push({ slug: report.slug, view: report.view, status: "failed", error: String(err.message) });
    }
  }

  await browser.close();

  // A run manifest so a silent failure is detectable downstream.
  const ok = results.filter((r) => r.status === "ok").length;
  const manifest = {
    runAt: new Date().toISOString(),
    expected: targets.length,
    succeeded: ok,
    failed: targets.length - ok,
    results,
  };
  await writeFile(path.join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2));

  log(`Done — ${ok}/${targets.length} exported to ${outDir}`);

  // Non-zero exit if anything failed, so a scheduler can alert.
  if (ok < targets.length) {
    const sessionish = results.some((r) => /login|sign in|timeout/i.test(r.error ?? ""));
    if (sessionish) {
      console.error("\n  Hint: the saved session may have expired. Re-run with --login.\n");
    }
    process.exit(2);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
