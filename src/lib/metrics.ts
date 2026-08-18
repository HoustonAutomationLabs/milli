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
}

/** Reduce the dataset to just what the scope permits. */
export function scopeDataset(data: CaseworkDataset, scope: DataScope): ScopedCases {
  let cases = data.cases;

  if (!scope.allCases) {
    if (scope.caseworkerId) {
      // Staff: only their own caseload.
      cases = cases.filter((c) => c.caseworkerId === scope.caseworkerId);
    } else if (scope.teamIds.length) {
      // Manager: cases across their team(s).
      const teams = new Set(scope.teamIds);
      cases = cases.filter((c) => teams.has(c.teamId));
    } else {
      cases = [];
    }
  }

  const caseIds = new Set(cases.map((c) => c.id));
  const compliance = data.compliance.filter((i) => caseIds.has(i.caseId));
  return { cases, compliance };
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
