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
  kind: "home_visit" | "medical_exam" | "medication_review" | "court_report" | "case_plan";
  label: string;
  dueDate: string; // ISO date
  state: ComplianceState;
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

/** The full dataset the metrics layer reduces over. */
export interface CaseworkDataset {
  teams: Team[];
  caseworkers: Caseworker[];
  cases: CaseRecord[];
  compliance: ComplianceItem[];
  trend: TrendPoint[];
}
