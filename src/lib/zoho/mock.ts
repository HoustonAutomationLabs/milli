/**
 * Mock fixtures — used when DATA_SOURCE=mock (the dev default).
 *
 * All data here is SYNTHETIC. No real children, workers, or PHI. This lets the
 * dashboard render end-to-end before the Zoho Analytics feed is confirmed in
 * Phase 0. Do not add real data to this file.
 */

import type { AuthUser } from "../rbac";
import type {
  CaseRecord,
  CaseStatus,
  CaseworkDataset,
  Caseworker,
  ComplianceItem,
  ComplianceState,
  Team,
  TrendPoint,
} from "./types";

export const MOCK_USERS: AuthUser[] = [
  { id: "u-ceo", name: "Dana Reyes", role: "ceo", teamIds: [] },
  { id: "u-mgr-north", name: "Priya Okafor", role: "manager", teamIds: ["t-north"], caseworkerId: "cw-1" },
  { id: "u-mgr-south", name: "Marcus Bell", role: "manager", teamIds: ["t-south"], caseworkerId: "cw-4" },
  { id: "u-staff-1", name: "Sam Ortiz", role: "staff", teamIds: ["t-north"], caseworkerId: "cw-2" },
  { id: "u-staff-2", name: "Jordan Lee", role: "staff", teamIds: ["t-central"], caseworkerId: "cw-7" },
];

const TEAMS: Team[] = [
  { id: "t-north", name: "North Region", managerCaseworkerId: "cw-1" },
  { id: "t-south", name: "South Region", managerCaseworkerId: "cw-4" },
  { id: "t-central", name: "Central Region", managerCaseworkerId: "cw-7" },
];

const CASEWORKERS: Caseworker[] = [
  { id: "cw-1", name: "Priya Okafor", teamId: "t-north" },
  { id: "cw-2", name: "Sam Ortiz", teamId: "t-north" },
  { id: "cw-3", name: "Alex Nguyen", teamId: "t-north" },
  { id: "cw-4", name: "Marcus Bell", teamId: "t-south" },
  { id: "cw-5", name: "Riley Chen", teamId: "t-south" },
  { id: "cw-6", name: "Tomas Vega", teamId: "t-south" },
  { id: "cw-7", name: "Jordan Lee", teamId: "t-central" },
  { id: "cw-8", name: "Fatima Diallo", teamId: "t-central" },
];

// --- deterministic pseudo-random so fixtures are stable across renders ------
function seeded(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

const rnd = seeded(42);
const pick = <T>(arr: T[]) => arr[Math.floor(rnd() * arr.length)];
const daysFromNow = (d: number) => {
  const dt = new Date("2026-08-18T00:00:00Z");
  dt.setUTCDate(dt.getUTCDate() + d);
  return dt.toISOString().slice(0, 10);
};

const STATUSES: CaseStatus[] = ["active", "active", "active", "intake", "on_hold"];
const PLACEMENTS: CaseRecord["placementType"][] = [
  "foster_home",
  "foster_home",
  "kinship",
  "residential",
];
const FIRST = ["A.", "B.", "C.", "D.", "E.", "F.", "G.", "H.", "J.", "K.", "L.", "M."];
const LAST = ["R.", "S.", "T.", "V.", "W.", "N.", "P.", "Q.", "Z."];

const LABELS: Record<ComplianceItem["kind"], string> = {
  home_visit: "Monthly home visit",
  medical_exam: "Medical exam",
  medication_review: "Medication review",
  court_report: "Court report",
  case_plan: "Case plan review",
};

const cases: CaseRecord[] = [];
const compliance: ComplianceItem[] = [];

for (let i = 0; i < 42; i++) {
  const worker = pick(CASEWORKERS);
  const status = STATUSES[i % STATUSES.length];
  const caseId = `case-${100 + i}`;

  // One-to-few compliance items per case; roll up to worst state.
  const itemCount = 1 + Math.floor(rnd() * 3);
  let worst: ComplianceState = "ok";
  const kinds: ComplianceItem["kind"][] = [
    "home_visit",
    "medical_exam",
    "medication_review",
    "court_report",
    "case_plan",
  ];
  for (let k = 0; k < itemCount; k++) {
    const offset = Math.floor(rnd() * 40) - 12; // -12..+27 days
    const state: ComplianceState = offset < 0 ? "overdue" : offset <= 7 ? "due_soon" : "ok";
    if (state === "overdue") worst = "overdue";
    else if (state === "due_soon" && worst !== "overdue") worst = "due_soon";
    const kind = kinds[(i + k) % kinds.length];
    compliance.push({
      id: `${caseId}-c${k}`,
      caseId,
      kind,
      label: LABELS[kind],
      dueDate: daysFromNow(offset),
      state,
    });
  }

  cases.push({
    id: caseId,
    displayId: `TX-${2600 + i}`,
    childName: `${pick(FIRST)} ${pick(LAST)}`,
    status,
    teamId: worker.teamId,
    caseworkerId: worker.id,
    openedOn: daysFromNow(-Math.floor(rnd() * 500) - 20),
    placementType: status === "intake" ? "unassigned" : pick(PLACEMENTS),
    compliance: worst,
  });
}

const trend: TrendPoint[] = (() => {
  const out: TrendPoint[] = [];
  let active = 118;
  for (let m = 11; m >= 0; m--) {
    const dt = new Date("2026-08-01T00:00:00Z");
    dt.setUTCMonth(dt.getUTCMonth() - m);
    const intakes = 6 + Math.floor(rnd() * 7);
    const discharges = 5 + Math.floor(rnd() * 6);
    active += intakes - discharges;
    out.push({ month: dt.toISOString().slice(0, 7), activeCases: active, intakes, discharges });
  }
  return out;
})();

export const MOCK_DATASET: CaseworkDataset = {
  teams: TEAMS,
  caseworkers: CASEWORKERS,
  cases,
  compliance,
  trend,
};
