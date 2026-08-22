/**
 * Casework data client — the single boundary between a data source and the app.
 *
 * (Named `zoho/` for historical reasons; Zoho is no longer the intended path.
 * See docs/extendedreach-audit.md.)
 *
 * Three modes, chosen by DATA_SOURCE:
 *   - "mock" (default): synthetic fixtures, no network. Used for development.
 *   - "exports": reads the Excel workbooks that
 *     `scripts/export-extendedreach.mjs` pulls out of ExtendedReach. This is
 *     the intended production path.
 *   - "zoho": the original Zoho Analytics plan. RETAINED BUT NOT RECOMMENDED —
 *     the agency declined the $500 + $125/mo feed, and the system audit found
 *     it unnecessary: every metric the dashboard needs is reachable through
 *     one-click Excel exports. The live path remains stubbed.
 *
 * Everything downstream depends only on `getDataset()` returning a
 * `CaseworkDataset`, so switching modes changes nothing in the UI.
 */

import type { CaseworkDataset } from "./types";
import { MOCK_DATASET } from "./mock";
import { loadExportDataset } from "../extendedreach/exports";

type Mode = "mock" | "exports" | "zoho";

function mode(): Mode {
  const m = process.env.DATA_SOURCE;
  if (m === "zoho") return "zoho";
  if (m === "exports") return "exports";
  return "mock";
}

/**
 * Exchange the long-lived refresh token for a short-lived access token.
 * Zoho access tokens expire in ~1h, so this should be cached with a small
 * safety margin (not implemented here — Phase 1 wiring).
 */
async function getAccessToken(): Promise<string> {
  const {
    ZOHO_OAUTH_CLIENT_ID,
    ZOHO_OAUTH_CLIENT_SECRET,
    ZOHO_OAUTH_REFRESH_TOKEN,
    ZOHO_ACCOUNTS_BASE_URL,
  } = process.env;

  if (!ZOHO_OAUTH_CLIENT_ID || !ZOHO_OAUTH_CLIENT_SECRET || !ZOHO_OAUTH_REFRESH_TOKEN) {
    throw new Error(
      "Zoho OAuth env vars missing. Set DATA_SOURCE=mock for local dev, or fill in " +
        "ZOHO_OAUTH_* (see .env.example) once Phase 0 provisions API access.",
    );
  }

  const url = new URL("/oauth/v2/token", ZOHO_ACCOUNTS_BASE_URL ?? "https://accounts.zoho.com");
  url.searchParams.set("refresh_token", ZOHO_OAUTH_REFRESH_TOKEN);
  url.searchParams.set("client_id", ZOHO_OAUTH_CLIENT_ID);
  url.searchParams.set("client_secret", ZOHO_OAUTH_CLIENT_SECRET);
  url.searchParams.set("grant_type", "refresh_token");

  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error(`Zoho token exchange failed: ${res.status}`);
  const json = (await res.json()) as { access_token?: string };
  if (!json.access_token) throw new Error("Zoho token exchange returned no access_token");
  return json.access_token;
}

/**
 * Run one Zoho Analytics query and return raw rows.
 * TODO(phase-0): confirm the real endpoint shape, workspace/view ids, and the
 * SQL/columns available from ExtendedReach's export, then map rows -> types.
 */
async function queryZoho<T>(_viewName: string): Promise<T[]> {
  const token = await getAccessToken();
  void token;
  // Placeholder. Real implementation issues a Data API request against
  // ZOHO_ANALYTICS_WORKSPACE_ID and maps the response rows into domain types.
  throw new Error(
    "Live Zoho Analytics querying is not wired yet. This is intentionally a " +
      "stub pending Phase 0 confirmation of the ExtendedReach -> Zoho feed. " +
      "Use DATA_SOURCE=mock for now.",
  );
}

/** The one entry point the app uses to obtain casework data. */
export async function getDataset(): Promise<CaseworkDataset> {
  if (mode() === "mock") {
    return MOCK_DATASET;
  }

  if (mode() === "exports") {
    const dir = process.env.ER_EXPORT_DIR ?? "./data/exports";
    const { dataset, diagnostics } = await loadExportDataset(dir);

    // Zero rows against a found workbook means the header names drifted — the
    // dashboard would render empty and look merely quiet rather than broken.
    const empty = Object.entries(diagnostics).filter(([, d]) => d.found && d.rows === 0);
    if (empty.length) {
      console.warn(
        `[datasource] ${empty.length} ExtendedReach export(s) parsed to zero rows: ` +
          `${empty.map(([slug]) => slug).join(", ")}. Check the column headers in ` +
          `src/lib/extendedreach/exports.ts against a real workbook.`,
      );
    }
    if (!dataset.cases.length) {
      throw new Error(
        `No cases loaded from ${dir}. Run scripts/export-extendedreach.mjs first, ` +
          `or set DATA_SOURCE=mock for development.`,
      );
    }
    return dataset;
  }

  // Live path — assembled from separate Zoho views once available.
  const [teams, caseworkers, cases, compliance, trend] = await Promise.all([
    queryZoho<CaseworkDataset["teams"][number]>("Teams"),
    queryZoho<CaseworkDataset["caseworkers"][number]>("Caseworkers"),
    queryZoho<CaseworkDataset["cases"][number]>("Cases"),
    queryZoho<CaseworkDataset["compliance"][number]>("Compliance"),
    queryZoho<CaseworkDataset["trend"][number]>("MonthlyTrend"),
  ]);
  return { teams, caseworkers, cases, compliance, trend };
}

export function dataSourceMode(): Mode {
  return mode();
}
