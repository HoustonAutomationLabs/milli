/**
 * ExtendedReach export reader.
 *
 * Reads the Excel workbooks produced by `scripts/export-extendedreach.mjs` and
 * maps them into the `CaseworkDataset` the dashboard already consumes. This is
 * the replacement for the Zoho Analytics path, which the agency declined on
 * cost and which the system audit found unnecessary — every metric the
 * dashboard needs is reachable through one-click Excel exports.
 * See docs/extendedreach-audit.md.
 *
 * Design notes
 * ------------
 * - Reports identify people by NAME only. `identity.ts` derives stable ids so
 *   nothing downstream has to carry a child's name to count or group them.
 * - Column layouts are matched by header text, not position, so an added
 *   column upstream does not silently shift every field.
 * - A missing or unreadable workbook degrades that slice to empty rather than
 *   failing the whole load — a stale caseload report should not blank the
 *   dashboard. The manifest written by the exporter is the place failures are
 *   surfaced.
 */

import { readdir } from "node:fs/promises";
import path from "node:path";

import type {
  CaseRecord,
  CaseworkDataset,
  Caseworker,
  ComplianceItem,
  ComplianceState,
  OnTimePoint,
  Team,
  TrendPoint,
} from "../zoho/types";
import { ABANDONED_AFTER_DAYS, daysOverdue } from "../aging";
import { caseDisplayId, homeDisplayId, normaliseName, workerId } from "./identity";
import { isReadableExport, readGrid, type Grid } from "./grid";
import { REPORT_SPECS, findHeaderRow, type ReportSpec } from "./schema";

// ---------------------------------------------------------------------------
// Workbook loading
// ---------------------------------------------------------------------------

/**
 * Find the most recent export for a slug. Filenames carry a date suffix
 * (`pastdue_case_20260822.xlsx`), so lexical sort is chronological.
 *
 * Both `.xlsx` and `.csv` count: most report views export Excel only, but the
 * Compliance Tracking and Reports Completed exports arrive as CSV. See
 * `grid.ts`.
 */
async function newestExport(dir: string, slug: string): Promise<string | null> {
  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch {
    return null;
  }
  const matches = entries
    .filter((f) => f.startsWith(`${slug}_`) && isReadableExport(f))
    .sort();
  const latest = matches[matches.length - 1];
  return latest ? path.join(dir, latest) : null;
}

/**
 * Rows below the header, keyed by the spec's logical field names.
 *
 * Header location and column resolution both come from `schema.ts`, so the
 * loader and the `inspect-export` reconciliation tool agree by construction.
 */
function rowsFor(grid: Grid, spec: ReportSpec): Record<string, string>[] {
  const found = findHeaderRow(spec, grid);
  if (!found) return [];

  const out: Record<string, string>[] = [];
  for (let r = found.header + 1; r < grid.length; r++) {
    const raw = grid[r];
    if (!raw || raw.every((c) => !c)) continue;

    const obj: Record<string, string> = {};
    for (const [field, i] of Object.entries(found.columns)) obj[field] = raw[i] ?? "";

    // Grouping headers repeat a section title in one cell and leave the
    // required fields blank; they are layout, not data.
    if (spec.required.every((f) => !obj[f])) continue;
    out.push(obj);
  }
  return out;
}

/**
 * Read the worker × month caseload cross-tab.
 *
 * Shape is `[year] | [worker] | [program] | Name | Jan … Dec`, with the first
 * three columns unlabelled and one row per (year, worker, client). The month
 * cells are 0/1 flags for whether that child sat on that worker's caseload
 * that month, so a caseload figure is a column sum, not a cell value.
 *
 * Returns monthly active-case totals and each worker's most recent caseload.
 */
function readCaseloadMatrix(grid: Grid): {
  monthly: Map<string, number>;
  perWorker: Map<string, number>;
} {
  const monthly = new Map<string, number>();
  const perWorker = new Map<string, number>();

  const hdr = grid.findIndex((row) => row.some((c) => c.toLowerCase() === "name"));
  if (hdr < 0) return { monthly, perWorker };

  const nameCol = grid[hdr].findIndex((c) => c.toLowerCase() === "name");
  const months = grid[hdr]
    .map((c, i) => ({ c: c.trim(), i }))
    .filter(({ c, i }) => i > nameCol && /^[a-z]{3}$/i.test(c));

  let latest = "";
  for (let r = hdr + 1; r < grid.length; r++) {
    const row = grid[r];
    if (!row) continue;
    const year = (row[0] ?? "").trim();
    const worker = (row[1] ?? "").trim();
    if (!/^(19|20)\d\d$/.test(year) || !worker) continue;

    for (const { c: mon, i } of months) {
      const on = (row[i] ?? "").trim();
      if (on !== "1") continue;
      const idx = MONTHS.indexOf(mon.toLowerCase());
      if (idx < 0) continue;
      const key = `${year}-${String(idx + 1).padStart(2, "0")}`;
      monthly.set(key, (monthly.get(key) ?? 0) + 1);
      if (key > latest) latest = key;
      perWorker.set(`${key}::${worker}`, (perWorker.get(`${key}::${worker}`) ?? 0) + 1);
    }
  }

  // Collapse per-worker counts to the most recent month present.
  const current = new Map<string, number>();
  for (const [key, n] of perWorker) {
    const [month, worker] = key.split("::");
    if (month === latest) current.set(worker, n);
  }
  return { monthly, perWorker: current };
}

const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

async function gridFor(dir: string, slug: string): Promise<Grid> {
  const file = await newestExport(dir, slug);
  if (!file) return [];
  try {
    return await readGrid(file);
  } catch {
    // A corrupt or partially-written workbook must not take the app down.
    return [];
  }
}

// ---------------------------------------------------------------------------
// Field mapping
// ---------------------------------------------------------------------------

/** ISO date from ExtendedReach's `M/D/YYYY`, tolerating already-ISO values. */
function toIso(value: string): string | null {
  if (!value) return null;
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return value.slice(0, 10);
  const m = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (!m) return null;
  const [, mo, d, y] = m;
  return `${y}-${mo.padStart(2, "0")}-${d.padStart(2, "0")}`;
}

// Date arithmetic and the age cutoffs now live in `lib/aging.ts` so the
// morning triage board can share them without importing the workbook reader.
// Re-exported here because the loader was their original home.
export { ABANDONED_AFTER_DAYS, daysOverdue } from "../aging";

/**
 * Classify an ExtendedReach task type into the dashboard's compliance kinds.
 * Unrecognised types map to "other" rather than being forced into a category —
 * a mislabelled obligation is worse than an unlabelled one.
 */
function classifyKind(type: string): ComplianceItem["kind"] {
  const t = type.toLowerCase();
  // Order matters: "Well Child Visit" is a medical exam, not a home visit, so
  // the specific medical patterns must be tested before the generic /visit/.
  if (/medical|well child|health|dental|exam|immuni/.test(t)) return "medical_exam";
  if (/\bvisit\b|contact|child logs/.test(t)) return "home_visit";
  if (/medication|prescri/.test(t)) return "medication_review";
  if (/court|legal|hearing/.test(t)) return "court_report";
  if (/plan of service|service plan|case plan|cans|assessment/.test(t)) return "case_plan";
  return "other";
}

/**
 * Statuses ExtendedReach actually uses on task reports, confirmed against a
 * real export: Due, Submitted, Draft, Expires, Rejected, Scheduled, Event.
 *
 * The distinction that matters is Submitted. A submitted item is finished work
 * sitting with a supervisor for approval — the caseworker has nothing left to
 * do. Counting those as overdue inflates the backlog by 165 items (of 997) and
 * would show staff as delinquent for work they completed.
 *
 * `state` therefore stays "ok" for a submission, exactly as before. What is
 * new is that the classification no longer *forgets* the item was submitted:
 * `awaitingApproval` carries it through so the morning board can show the
 * approval queue as its own tier. Suppressing it from the backlog and losing
 * it entirely were never the same requirement.
 */
function classify(
  dueIso: string | null,
  statusText: string,
): { state: ComplianceState; awaitingApproval: boolean; calendarOnly: boolean } {
  const status = statusText.trim().toLowerCase();
  const base = { awaitingApproval: false, calendarOnly: false };

  // Done and awaiting approval — not the caseworker's outstanding work.
  if (status === "submitted") return { ...base, state: "ok", awaitingApproval: true };

  // Calendar entries, not date-driven obligations.
  if (status === "scheduled" || status === "event") {
    return { ...base, state: "ok", calendarOnly: true };
  }

  if (!dueIso) return { ...base, state: "due_soon" };
  const d = daysOverdue(dueIso);
  if (d > 0) return { ...base, state: "overdue" };
  if (d > -30) return { ...base, state: "due_soon" };
  return { ...base, state: "ok" };
}

// ---------------------------------------------------------------------------
// Dataset assembly
// ---------------------------------------------------------------------------

export interface ExportLoadResult {
  dataset: CaseworkDataset;
  /** Per-slug row counts and whether the workbook was found, for the run log. */
  diagnostics: Record<string, { found: boolean; rows: number }>;
}

/**
 * Build a `CaseworkDataset` from a directory of ExtendedReach exports.
 *
 * Column names come from `schema.ts`, which lists accepted header variants per
 * field. If a real export uses a header not listed there, this yields zero rows
 * for that report — run `npm run inspect:export -- <file>` to see the actual
 * headers and the exact alias line to add.
 */
export async function loadExportDataset(dir: string): Promise<ExportLoadResult> {
  const diagnostics: Record<string, { found: boolean; rows: number }> = {};
  const note = (slug: string, grid: Grid, rows: unknown[]) => {
    diagnostics[slug] = { found: grid.length > 0, rows: rows.length };
  };

  const [gOpen, gPastCase, gPastHome, gInproc, gCaseload, gOnTime, gNeedApproval] =
    await Promise.all([
      gridFor(dir, "opencases"),
      gridFor(dir, "pastdue_case"),
      gridFor(dir, "pastdue_home"),
      gridFor(dir, "inprocess"),
      gridFor(dir, "caseload"),
      gridFor(dir, "ontime"),
      gridFor(dir, "needapproval_case"),
    ]);

  // --- caseworkers and teams ------------------------------------------------
  // ExtendedReach has no team entity; teams are inferred from the case
  // manager on each case. One team per manager until a real structure exists.
  const workers = new Map<string, Caseworker>();
  const ensureWorker = (name: string): Caseworker | null => {
    const clean = name.trim();
    if (!clean) return null;
    const id = workerId(clean);
    let w = workers.get(id);
    if (!w) {
      w = { id, name: clean, teamId: `team-${id}` };
      workers.set(id, w);
    }
    return w;
  };

  // --- cases ----------------------------------------------------------------
  const openRows = rowsFor(gOpen, REPORT_SPECS.opencases);
  note("opencases", gOpen, openRows);

  const cases: CaseRecord[] = openRows.map((r) => {
    const childName = r.client ?? "";
    const worker = ensureWorker(r.worker ?? "");
    const placement = (r.placementType ?? "").toLowerCase();
    // The roster carries a real Case # for every row. Prefer it over a hash of
    // the name: it survives spelling drift and distinguishes siblings, which
    // name matching cannot.
    const caseNo = (r.caseNumber ?? "").trim();
    const id = caseNo ? `FC-${caseNo}` : caseDisplayId(childName);
    return {
      id,
      displayId: id,
      childName,
      status: "active",
      teamId: worker?.teamId ?? "team-unassigned",
      caseworkerId: worker?.id ?? "wkr-unassigned",
      openedOn: toIso(r.openedOn ?? "") ?? "",
      placementType: /kinship/.test(placement)
        ? "kinship"
        : /residential|rtc/.test(placement)
          ? "residential"
          : /foster/.test(placement)
            ? "foster_home"
            : "unassigned",
      compliance: "ok",
    };
  });

  const caseByName = new Map(cases.map((c) => [normaliseName(c.childName), c]));

  // --- compliance obligations ----------------------------------------------
  //
  // "Due Soon / Past Due" is a filtered view of "In Process", not a separate
  // set of work: 98.4% of its rows appear in both. Ingesting them naively
  // double-counts 1,139 obligations and would inflate the headline backlog by
  // roughly half. Rows are therefore keyed on the obligation itself — subject,
  // type and due date — and the first sighting wins.
  const compliance: ComplianceItem[] = [];
  const seenObligation = new Set<string>();
  // Submissions already seen on a task report, keyed subject|type. The
  // approval queue re-lists the same work, so this is what stops it being
  // counted twice — and it holds the item itself so the approver can be
  // attached to the row that already exists.
  const submittedItems = new Map<string, ComplianceItem>();
  let seq = 0;
  let duplicatesSkipped = 0;

  const ingestTasks = (grid: Grid, spec: ReportSpec, subject: "client" | "home") => {
    const rows = rowsFor(grid, spec);
    note(spec.slug, grid, rows);
    for (const r of rows) {
      const due = toIso(r.dueDate ?? "");
      const name = (subject === "home" ? r.home : r.client) ?? "";
      const linked = subject === "client" ? caseByName.get(normaliseName(name)) : undefined;
      ensureWorker(r.worker ?? "");
      const type = r.type ?? "";
      // A home obligation is not a case obligation; give it an HM- id so the
      // distinction survives instead of looking like a failed case join.
      const subjectId = subject === "home" ? homeDisplayId(name) : caseDisplayId(name);

      const obligationKey = `${linked?.id ?? subjectId}|${type}|${due ?? ""}`;
      if (seenObligation.has(obligationKey)) {
        duplicatesSkipped++;
        continue;
      }
      seenObligation.add(obligationKey);

      const { state, awaitingApproval, calendarOnly } = classify(due, r.status ?? "");
      const record: ComplianceItem = {
        id: `ci-${spec.slug}-${seq++}`,
        caseId: linked?.id ?? subjectId,
        kind: classifyKind(type),
        label: type || "Task",
        dueDate: due ?? "",
        state,
        // The task reports know an item is submitted but not who it is queued
        // with — they carry no approver column. `needapproval_case` supplies
        // that below.
        ...(awaitingApproval ? { awaitingApproval: true } : {}),
        ...(calendarOnly ? { calendarOnly: true } : {}),
      };
      compliance.push(record);
      if (awaitingApproval) submittedItems.set(`${linked?.id ?? subjectId}|${type}`, record);
    }
  };

  // Order matters only for which row wins a duplicate; the narrower, more
  // recently-scoped report is ingested first so its status is the one kept.
  ingestTasks(gPastCase, REPORT_SPECS.pastdue_case, "client");
  ingestTasks(gPastHome, REPORT_SPECS.pastdue_home, "home");
  ingestTasks(gInproc, REPORT_SPECS.inprocess, "client");

  if (duplicatesSkipped) {
    diagnostics.deduplicated = { found: true, rows: duplicatesSkipped };
  }

  // --- approval queue -------------------------------------------------------
  //
  // The task reports show that an item is Submitted; only this report shows
  // WHO it is waiting on, and it is the whole queue rather than its past-due
  // slice — 394 submissions against 18 approvers, one of whom holds 202.
  // That distribution is the finding the morning board's tier 2 exists to
  // surface, and it is unreachable from any other export.
  //
  // The overlap has to be handled or the same finished work is counted twice:
  // every Submitted row already ingested above reappears here. This report
  // carries no due date to key on, so the match is subject + type — coarser
  // than the subject|type|due key used for the task reports, and deliberately
  // biased toward dropping a real row rather than inventing one. The count is
  // reported so the trade is measurable rather than assumed.
  const approvalRows = rowsFor(gNeedApproval, REPORT_SPECS.needapproval_case);
  note("needapproval_case", gNeedApproval, approvalRows);

  let approvalsAlreadySeen = 0;
  for (const r of approvalRows) {
    const name = r.client ?? "";
    const linked = caseByName.get(normaliseName(name));
    const type = r.type ?? "";
    const subjectId = linked?.id ?? caseDisplayId(name);
    const performer = (r.worker ?? "").trim();
    ensureWorker(performer);

    const existing = submittedItems.get(`${subjectId}|${type}`);
    if (existing) {
      // Already ingested from a task report. Attach the approver to the row
      // that is already there rather than adding a second one.
      existing.approver = (r.approver ?? "").trim() || existing.approver;
      existing.submittedOn = toIso(r.submittedOn ?? "") ?? existing.submittedOn;
      if (performer) existing.performedBy = performer;
      approvalsAlreadySeen++;
      continue;
    }

    const record: ComplianceItem = {
      id: `ci-approval-${seq++}`,
      caseId: subjectId,
      kind: classifyKind(type),
      label: type || "Task",
      // Every row here is Submitted by definition, so the caseworker's work
      // is done: no due date drives it any more, and `state` stays "ok" for
      // the same reason it does on a submitted task row.
      dueDate: "",
      state: "ok",
      awaitingApproval: true,
      approver: (r.approver ?? "").trim() || undefined,
      submittedOn: toIso(r.submittedOn ?? "") ?? undefined,
      performedBy: performer || undefined,
    };
    compliance.push(record);
    submittedItems.set(`${subjectId}|${type}`, record);
  }

  if (approvalsAlreadySeen) {
    diagnostics.approvalsDeduplicated = { found: true, rows: approvalsAlreadySeen };
  }

  // Roll the worst state on each case up onto the case record.
  const rank: Record<ComplianceState, number> = { ok: 0, due_soon: 1, overdue: 2 };
  for (const item of compliance) {
    const c = cases.find((x) => x.id === item.caseId);
    if (c && rank[item.state] > rank[c.compliance]) c.compliance = item.state;
  }

  // --- caseload census ------------------------------------------------------
  // Only used to register workers who hold cases but appear on no task row.
  const { monthly, perWorker } = readCaseloadMatrix(gCaseload);
  diagnostics.caseload = { found: gCaseload.length > 0, rows: monthly.size };
  for (const worker of perWorker.keys()) ensureWorker(worker);

  const caseworkers = [...workers.values()];
  const teams: Team[] = caseworkers.map((w) => ({
    id: w.teamId,
    name: `${w.name}'s caseload`,
    managerCaseworkerId: w.id,
  }));

  // --- trend ----------------------------------------------------------------
  // The caseload cross-tab is the only source of history in the export set —
  // summing its monthly flags gives a real active-case series. Intakes and
  // discharges are not derivable from it and stay zero rather than invented.
  const trend: TrendPoint[] = [...monthly.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, activeCases]) => ({ month, activeCases, intakes: 0, discharges: 0 }));

  // --- on-time completion ---------------------------------------------------
  // The variance export is one row per completed item, so the percentage is
  // derived rather than read: an item is on time when it was finished on or
  // before its due date (variance <= 0). Deriving it this way means it can be
  // cut by month instead of arriving as a single agency-wide figure.
  const onTimeRows = rowsFor(gOnTime, REPORT_SPECS.ontime);
  note("ontime", gOnTime, onTimeRows);

  const byMonth = new Map<string, { onTime: number; total: number; daysLate: number }>();
  for (const r of onTimeRows) {
    const iso = toIso(r.date ?? "");
    const variance = Number.parseInt((r.variance ?? "").trim(), 10);
    if (!iso || Number.isNaN(variance)) continue;
    const month = iso.slice(0, 7);
    const bucket = byMonth.get(month) ?? { onTime: 0, total: 0, daysLate: 0 };
    bucket.total++;
    if (variance <= 0) bucket.onTime++;
    bucket.daysLate += variance;
    byMonth.set(month, bucket);
  }

  const onTime: OnTimePoint[] = [...byMonth.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, b]) => ({
      month,
      onTimePct: Math.round((b.onTime / b.total) * 1000) / 10,
      sample: b.total,
      avgDaysLate: Math.round((b.daysLate / b.total) * 10) / 10,
    }));

  return {
    dataset: { teams, caseworkers, cases, compliance, trend, onTime },
    diagnostics,
  };
}
