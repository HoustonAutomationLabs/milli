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
  HomeRecord,
  OnTimePoint,
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
// Anchored to the real current date rather than a fixed one: the morning
// board tiers items by how overdue they are today, so a hard-coded base would
// slide every fixture into the "needs a decision" tier as months passed and
// make the demo misrepresent what the board does.
const daysFromNow = (d: number) => {
  const now = new Date();
  const dt = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
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

/**
 * Supervisors who approve submitted work.
 *
 * Weighted, not uniform. The real approval queue is held by 18 approvers with
 * one holding 51% of it, and a fixture with an even spread would show the
 * morning board's tier 2 working while hiding the concentration that is the
 * entire reason that tier exists.
 */
const APPROVERS = [
  "Priya Okafor",
  "Priya Okafor",
  "Priya Okafor",
  "Priya Okafor",
  "Priya Okafor",
  "Marcus Bell",
  "Marcus Bell",
  "Dana Reyes",
];

const LABELS: Record<ComplianceItem["kind"], string> = {
  home_visit: "Monthly home visit",
  medical_exam: "Medical exam",
  medication_review: "Medication review",
  court_report: "Court report",
  case_plan: "Case plan review",
  other: "Other obligation",
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
    const kind = kinds[(i + k) % kinds.length];
    const roll = rnd();

    // Roughly one obligation in six is finished work sitting with a
    // supervisor. `state` stays "ok" for these, matching how the loader
    // classifies a Submitted row: the caseworker has nothing left to do, so
    // it is not their backlog — but it is still blocked, and the morning
    // board's tier 2 is where it shows up.
    if (roll < 0.16) {
      compliance.push({
        id: `${caseId}-c${k}`,
        caseId,
        kind,
        label: LABELS[kind],
        dueDate: daysFromNow(-Math.floor(rnd() * 45) - 1),
        state: "ok",
        awaitingApproval: true,
        approver: APPROVERS[Math.floor(rnd() * APPROVERS.length)],
        submittedOn: daysFromNow(-Math.floor(rnd() * 60) - 1),
      });
      continue;
    }

    // A long tail of records open since 2020-2023. The real export puts 31%
    // of past-due items over a year old; without a few here the board's
    // fourth tier renders empty and the demo implies the agency has no
    // abandoned backlog.
    const offset =
      roll < 0.28
        ? -(400 + Math.floor(rnd() * 1900)) // 1.1 to 6.3 years overdue
        : Math.floor(rnd() * 40) - 12; // -12..+27 days

    const state: ComplianceState = offset < 0 ? "overdue" : offset <= 7 ? "due_soon" : "ok";
    if (state === "overdue") worst = "overdue";
    else if (state === "due_soon" && worst !== "overdue") worst = "due_soon";
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

/**
 * On-time completion, month by month.
 *
 * Sits in the low 40s on purpose. The real agency runs 41.1% on time across
 * 3,184 completed items, and the morning board states that figure next to the
 * tier counts — a fixture in the 90s would let the demo tell a story the data
 * does not support.
 */
const onTime: OnTimePoint[] = trend.map((t, idx) => {
  const pct = 37 + Math.round(rnd() * 11);
  return {
    month: t.month,
    onTimePct: pct,
    sample: 260 + Math.floor(rnd() * 140),
    avgDaysLate: Math.round((61 - idx * 4) * 10) / 10,
  };
});

const LICENSE_TYPES = ["Foster Family", "Kinship", "Therapeutic", "Emergency"];
const AGE_RANGES = ["0-5", "6-12", "13-17", "0-17"];
const GENDERS = ["Any", "Male", "Female"];

const homes: HomeRecord[] = Array.from({ length: 14 }, (_, i) => {
  const beds = Math.floor(rnd() * 4);
  return {
    id: `hm-${i}`,
    displayId: `HM-${400 + i}`,
    licenseType: pick(LICENSE_TYPES),
    bedsAvailable: beds,
    ageRange: pick(AGE_RANGES),
    gender: pick(GENDERS),
    lastPlacement: daysFromNow(-Math.floor(rnd() * 200) - 5),
  };
});

export const MOCK_DATASET: CaseworkDataset = {
  teams: TEAMS,
  caseworkers: CASEWORKERS,
  cases,
  compliance,
  trend,
  onTime,
  homes,
};
