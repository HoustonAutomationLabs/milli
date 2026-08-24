/**
 * Bind the stubbed sign-in accounts to workers that exist in the loaded data.
 *
 * The dev accounts carry mock ids — `cw-1`…`cw-8`, `t-north` — invented in
 * `mock.ts`. Under `DATA_SOURCE=exports` the workers and teams are derived
 * from the export itself, so those ids match nothing: every manager and
 * caseworker signs in to a fully working dashboard reporting zero of
 * everything. The CEO is unaffected, because an agency-wide scope never
 * consults an id.
 *
 * ## Why this is gated the way it is
 *
 * This function WIDENS a user's scope, from nothing to a real caseload. That
 * is exactly the operation access control exists to prevent, so it must never
 * be reachable by a real user: someone whose id is merely mistyped or
 * not-yet-provisioned would otherwise be handed somebody else's records.
 *
 * The gate is membership of `MOCK_USERS` — the hard-coded list the stubbed
 * provider hands out. It is self-limiting rather than a flag someone has to
 * remember: when `auth.ts` is replaced with a real identity provider,
 * `getCurrentUser()` stops returning these accounts and the binding becomes
 * unreachable. Delete this module at that point.
 */

import { MOCK_USERS } from "./zoho/mock";
import { scopeForUser, type AuthUser, type DataScope } from "./rbac";
import type { CaseworkDataset } from "./zoho/types";

export interface ResolvedScope {
  scope: DataScope;
  /**
   * Present only when a demo account was mapped onto real workers, so the UI
   * can say so. A viewer must never be left thinking the account name on
   * screen is the person whose caseload they are looking at.
   */
  boundTo?: string[];
}

function isDemoAccount(user: AuthUser): boolean {
  return MOCK_USERS.some((u) => u.id === user.id);
}

/** Workers who actually hold cases, busiest first. */
function rankedWorkers(data: CaseworkDataset): string[] {
  const counts = new Map<string, number>();
  for (const c of data.cases) counts.set(c.caseworkerId, (counts.get(c.caseworkerId) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([id]) => id);
}

/**
 * The scope a page should actually use.
 *
 * Identical to `scopeForUser` for real users, for the CEO, and whenever the
 * account's own ids are present in the data — binding only happens when the
 * alternative is an empty dashboard.
 */
export function resolveScope(user: AuthUser, data: CaseworkDataset): ResolvedScope {
  const scope = scopeForUser(user);
  if (scope.allCases || !isDemoAccount(user)) return { scope };

  const workerIds = new Set(data.caseworkers.map((w) => w.id));
  const teamIds = new Set(data.teams.map((t) => t.id));

  const idResolves = scope.caseworkerId ? workerIds.has(scope.caseworkerId) : false;
  const teamsResolve = scope.teamIds.length > 0 && scope.teamIds.every((t) => teamIds.has(t));
  if (idResolves || teamsResolve) return { scope };

  const ranked = rankedWorkers(data);
  if (!ranked.length) return { scope };

  const teamOf = new Map(data.caseworkers.map((w) => [w.id, w.teamId]));
  // Stable ordinal within each role, so an account always lands on the same
  // worker across requests and the demo does not shuffle between refreshes.
  const peers = MOCK_USERS.filter((u) => u.role === user.role);
  const ordinal = Math.max(0, peers.findIndex((u) => u.id === user.id));

  if (user.role === "staff") {
    const chosen = ranked[ordinal % ranked.length];
    return {
      scope: { ...scope, caseworkerId: chosen, teamIds: [teamOf.get(chosen) ?? ""] },
      boundTo: [chosen],
    };
  }

  // Managers oversee several workers. ExtendedReach has no team entity — the
  // loader gives each worker their own team — so a manager's view is assembled
  // from a slice of those rather than read from a real structure.
  const perManager = Math.max(1, Math.ceil(ranked.length / Math.max(peers.length, 1)));
  const slice = ranked.slice(ordinal * perManager, ordinal * perManager + perManager);
  const chosen = slice.length ? slice : ranked.slice(0, perManager);

  return {
    scope: {
      ...scope,
      caseworkerId: undefined,
      teamIds: chosen.map((id) => teamOf.get(id) ?? "").filter(Boolean),
    },
    boundTo: chosen,
  };
}

/** Display names for the workers an account was bound to. */
export function boundWorkerNames(ids: string[], data: CaseworkDataset): string[] {
  const names = new Map(data.caseworkers.map((w) => [w.id, w.name]));
  return ids.map((id) => names.get(id) ?? id);
}
