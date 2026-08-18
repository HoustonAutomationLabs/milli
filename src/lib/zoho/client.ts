/**
 * Zoho Analytics data client.
 *
 * ExtendedReach's only confirmed data tap is Zoho Analytics ("SOHO Analytics"),
 * which the agency must enable via a plan upgrade (see the strategy brief,
 * Phase 0 item #1). Zoho Analytics exposes a REST/Data API; this module is the
 * single boundary between that API and the rest of the app.
 *
 * Two modes, chosen by DATA_SOURCE:
 *   - "mock" (default): returns synthetic fixtures, no network.
 *   - "zoho": queries Zoho Analytics live. The live path is stubbed with the
 *     exact TODOs needed once Phase 0 confirms workspace/view names + OAuth.
 *
 * Everything downstream depends only on `getDataset()` returning a
 * `CaseworkDataset`, so flipping to live data changes nothing in the UI.
 */

import type { CaseworkDataset } from "./types";
import { MOCK_DATASET } from "./mock";

type Mode = "mock" | "zoho";

function mode(): Mode {
  return process.env.DATA_SOURCE === "zoho" ? "zoho" : "mock";
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
