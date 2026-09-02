/**
 * Domain types for the casework dashboard.
 *
 * These model the *shape the dashboard needs*, not ExtendedReach's internal
 * schema. The Zoho Analytics client maps raw rows into these types, so the
 * rest of the app is insulated from how the export is structured. Confirm the
 * real field availability in Phase 0 and adjust the mapping — not the UI.
 *
 * PHI note: `Case.childName` and similar are PHI. Prefer displaying the
 * `displayId` and initials in broad views; reveal full identifiers only where
 * the role and task genuinely require them (minimum necessary).
 */

export type CaseStatus = "active" | "intake" | "on_hold" | "discharged";

export type ComplianceState = "ok" | "due_soon" | "overdue";

export interface Team {
  id: string;
  name: string;
  managerCaseworkerId: string;
}

export interface Caseworker {
  id: string;
  name: string;
  teamId: string;
}

/** A required, date-driven obligation on a case (visit, medical, court, etc.). */
export interface ComplianceItem {
  id: string;
  caseId: string;
  kind: "home_visit" | "medical_exam" | "medication_review" | "court_report" | "case_plan" | "other";
  label: string;
  dueDate: string; // ISO date
  state: ComplianceState;

  /**
   * The work is done and sitting with a supervisor for approval.
   *
   * `state` stays "ok" for these on purpose: the caseworker has nothing left
   * to do, so counting them as overdue would show staff as delinquent for
   * work they completed (165 of 997 past-due case tasks, per the audit). But
   * "ok" alone loses the fact that the item is *blocked*, which is the
   * agency's harder bottleneck. This flag is what keeps it visible.
   */
  awaitingApproval?: boolean;
  /** Who the submission is queued with. Present only when awaiting approval. */
  approver?: string;
  /** ISO date the work was submitted. Drives how long it has been waiting. */
  submittedOn?: string;
  /** Caseworker who performed the work, where the report names a performer. */
  performedBy?: string;

  /**
   * A calendar entry rather than a date-driven obligation — ExtendedReach's
   * `Scheduled` and `Event` statuses.
   *
   * It carries a date, so anything that tiers work by how overdue it is will
   * happily sort it into a backlog unless told not to. Whether a row is an
   * obligation at all is a fact about its status, decided once at load; only
   * *when* it is due may be recomputed later.
   */
  calendarOnly?: boolean;
}

export interface CaseRecord {
  id: string;
  /** Non-PHI display identifier safe for broad views. */
  displayId: string;
  /** PHI — child's name. Handle with care; scope tightly. */
  childName: string;
  status: CaseStatus;
  teamId: string;
  caseworkerId: string;
  /** ISO date the case opened. */
  openedOn: string;
  placementType: "foster_home" | "kinship" | "residential" | "unassigned";
  /** Rolled-up worst compliance state across this case's items. */
  compliance: ComplianceState;
}

/** A monthly agency data point for trend charts (non-PHI, aggregate only). */
export interface TrendPoint {
  month: string; // e.g. "2026-03"
  activeCases: number;
  intakes: number;
  discharges: number;
}

/**
 * On-time completion for one month, derived from per-item due-date variance.
 * Non-PHI and aggregate only.
 */
export interface OnTimePoint {
  month: string; // e.g. "2026-08"
  /** Items completed on or before their due date, as a percentage. */
  onTimePct: number;
  /** How many completed items the percentage is based on. */
  sample: number;
  /** Mean days late across the sample; negative means early on average. */
  avgDaysLate: number;
}

/**
 * A licensed foster home's current availability, from the "Available Homes —
 * Open Beds" export. Not case-scoped — a home is not owned by a caseworker's
 * team the way a case is — so it is read the same way by every role that can
 * see the register at all.
 *
 * The export also carries the home's street address, phone, and an
 * `Active Placements` column naming the children currently there. None of
 * that is modelled here: it is not necessary for a capacity-at-a-glance view,
 * and the "minimum necessary" principle this app follows elsewhere applies
 * just as much to foster parents' contact details as to a child's.
 */
export interface HomeRecord {
  id: string;
  /** Non-PHI display identifier safe for broad views. */
  displayId: string;
  licenseType: string;
  bedsAvailable: number | null;
  ageRange: string;
  gender: string;
  /** ISO date of the home's most recent placement, when known. */
  lastPlacement: string;
}

/** The full dataset the metrics layer reduces over. */
export interface CaseworkDataset {
  teams: Team[];
  caseworkers: Caseworker[];
  cases: CaseRecord[];
  compliance: ComplianceItem[];
  trend: TrendPoint[];
  /** Present when the on-time variance export is available. */
  onTime?: OnTimePoint[];
  /** Present when the open-beds export is available. */
  homes?: HomeRecord[];
}
