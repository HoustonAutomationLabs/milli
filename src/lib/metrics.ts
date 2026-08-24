/**
 * Role-scoped metrics.
 *
 * This layer takes the full dataset + a user's `DataScope` and returns ONLY the
 * records and aggregates that user is allowed to see. Scoping happens here, on
 * the server, so the UI never receives out-of-scope data in the first place —
 * the "minimum necessary" rule enforced in code, not just hidden in the view.
 */

import type { DataScope } from "./rbac";
import type { CaseRecord, CaseworkDataset, ComplianceItem, TrendPoint } from "./zoho/types";

export interface ScopedCases {
  cases: CaseRecord[];
  compliance: ComplianceItem[];
  /**
   * Obligations in scope that belong to no case on the open-cases roster.
   *
   * Agency-wide scopes only; always 0 for a team or personal scope, which
   * cannot include what they cannot attribute. Reported so an executive total
   * and the sum of the team totals are never mistaken for the same figure.
   */
  unattributed: number;
}

/**
 * Reduce the dataset to just what the scope permits.
 *
 * Two different filters are at work and they must not be confused:
 *
 * - **Permission.** A manager sees their teams, a caseworker sees their own
 *   caseload. Both are enforced by narrowing to the cases they may read and
 *   then to those cases' obligations, because an obligation that joins to no
 *   case cannot be shown to either without guessing whose it is.
 *
 * - **Joining.** An agency-wide scope has no permission filter to apply, so
 *   it must not inherit the join as though it were one. It previously did,
 *   and that silently withheld 1,627 of 2,766 obligations (59%) from the
 *   executive view: 371 home-subject tasks, which belong to a home rather
 *   than a child and can never join to a case, plus 1,256 case tasks whose
 *   client is not on the *open*-cases roster — closed cases still carrying
 *   open work. Those are real obligations; the audit counts them. Dropping
 *   them made the dashboard report roughly half the backlog the same loader
 *   had just measured.
 */
export function scopeDataset(data: CaseworkDataset, scope: DataScope): ScopedCases {
  if (scope.allCases) {
    const caseIds = new Set(data.cases.map((c) => c.id));
    return {
      cases: data.cases,
      compliance: data.compliance,
      unattributed: data.compliance.filter((i) => !caseIds.has(i.caseId)).length,
    };
  }

  let cases: CaseRecord[];
  if (scope.caseworkerId) {
    // Staff: only their own caseload.
    cases = data.cases.filter((c) => c.caseworkerId === scope.caseworkerId);
  } else if (scope.teamIds.length) {
    // Manager: cases across their team(s).
    const teams = new Set(scope.teamIds);
    cases = data.cases.filter((c) => teams.has(c.teamId));
  } else {
    cases = [];
  }

  const caseIds = new Set(cases.map((c) => c.id));
  const compliance = data.compliance.filter((i) => caseIds.has(i.caseId));
  return { cases, compliance, unattributed: 0 };
}

export interface Kpis {
  activeCases: number;
  intakes: number;
  overdueItems: number;
  dueSoonItems: number;
  complianceRate: number; // 0..1 — share of cases not overdue
  avgCaseload: number | null; // null when not meaningful (staff / single worker)
}

export function computeKpis(scoped: ScopedCases): Kpis {
  const active = scoped.cases.filter((c) => c.status === "active").length;
  const intakes = scoped.cases.filter((c) => c.status === "intake").length;
  const overdueItems = scoped.compliance.filter((i) => i.state === "overdue").length;
  const dueSoonItems = scoped.compliance.filter((i) => i.state === "due_soon").length;

  const total = scoped.cases.length;
  const compliant = scoped.cases.filter((c) => c.compliance !== "overdue").length;
  const complianceRate = total === 0 ? 1 : compliant / total;

  const workerIds = new Set(scoped.cases.map((c) => c.caseworkerId));
  const avgCaseload = workerIds.size > 1 ? total / workerIds.size : null;

  return { activeCases: active, intakes, overdueItems, dueSoonItems, complianceRate, avgCaseload };
}

export interface WorkerLoad {
  caseworkerId: string;
  name: string;
  teamName: string;
  total: number;
  overdue: number;
}

/** Per-worker caseload breakdown (managers / CEO). */
export function caseloadByWorker(data: CaseworkDataset, scoped: ScopedCases): WorkerLoad[] {
  const teamName = new Map(data.teams.map((t) => [t.id, t.name]));
  const workerName = new Map(data.caseworkers.map((w) => [w.id, w.name]));
  const byWorker = new Map<string, WorkerLoad>();

  for (const c of scoped.cases) {
    const row =
      byWorker.get(c.caseworkerId) ??
      {
        caseworkerId: c.caseworkerId,
        name: workerName.get(c.caseworkerId) ?? c.caseworkerId,
        teamName: teamName.get(c.teamId) ?? c.teamId,
        total: 0,
        overdue: 0,
      };
    row.total += 1;
    if (c.compliance === "overdue") row.overdue += 1;
    byWorker.set(c.caseworkerId, row);
  }

  return [...byWorker.values()].sort((a, b) => b.total - a.total);
}

/** Upcoming/overdue compliance items, soonest first. */
export function upcomingItems(scoped: ScopedCases, limit = 12): ComplianceItem[] {
  return [...scoped.compliance]
    .filter((i) => i.state !== "ok")
    .sort((a, b) => a.dueDate.localeCompare(b.dueDate))
    .slice(0, limit);
}

export function agencyTrend(data: CaseworkDataset): TrendPoint[] {
  // Trend is agency-level aggregate (non-PHI); shown to CEO only.
  return data.trend;
}
