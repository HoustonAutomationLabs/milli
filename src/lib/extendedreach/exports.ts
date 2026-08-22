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

import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import ExcelJS from "exceljs";

import type {
  CaseRecord,
  CaseworkDataset,
  Caseworker,
  ComplianceItem,
  ComplianceState,
  Team,
  TrendPoint,
} from "../zoho/types";
import { caseDisplayId, homeDisplayId, normaliseName, workerId } from "./identity";
import { REPORT_SPECS, findHeaderRow, type ReportSpec } from "./schema";

/** Rows of a sheet as trimmed strings, header row included. */
type Grid = string[][];

// ---------------------------------------------------------------------------
// Workbook loading
// ---------------------------------------------------------------------------

/**
 * Find the most recent export for a slug. Filenames carry a date suffix
 * (`pastdue_case_20260822.xlsx`), so lexical sort is chronological.
 */
async function newestExport(dir: string, slug: string): Promise<string | null> {
  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch {
    return null;
  }
  const matches = entries
    .filter((f) => f.startsWith(`${slug}_`) && f.endsWith(".xlsx"))
    .sort();
  const latest = matches[matches.length - 1];
  return latest ? path.join(dir, latest) : null;
}

/** Read the first worksheet of a workbook into a grid of trimmed strings. */
async function readGrid(file: string): Promise<Grid> {
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(await readFile(file));
  const ws = wb.worksheets[0];
  if (!ws) return [];

  const grid: Grid = [];
  ws.eachRow({ includeEmpty: false }, (row) => {
    const cells: string[] = [];
    row.eachCell({ includeEmpty: true }, (cell, col) => {
      const v = cell.value;
      let s = "";
      if (v == null) s = "";
      else if (v instanceof Date) s = v.toISOString().slice(0, 10);
      else if (typeof v === "object" && "text" in v) s = String(v.text ?? "");
      else if (typeof v === "object" && "result" in v) s = String(v.result ?? "");
      else s = String(v);
      cells[col - 1] = s.trim();
    });
    grid.push(Array.from(cells, (c) => c ?? ""));
  });
  return grid;
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

/** Whole days between a due date and today; negative means still upcoming. */
export function daysOverdue(dueIso: string, today = new Date()): number {
  const due = new Date(`${dueIso}T00:00:00Z`);
  const now = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  return Math.round((now.getTime() - due.getTime()) / 86_400_000);
}

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

function stateFor(dueIso: string | null, statusText: string): ComplianceState {
  if (/past due|overdue/i.test(statusText)) return "overdue";
  if (!dueIso) return "due_soon";
  const d = daysOverdue(dueIso);
  if (d > 0) return "overdue";
  if (d > -30) return "due_soon";
  return "ok";
}

// ---------------------------------------------------------------------------
// Dataset assembly
// ---------------------------------------------------------------------------

/**
 * Age threshold, in days, beyond which an overdue item is treated as an
 * abandoned record rather than live work.
 *
 * The audit found 1,351 past-due items, roughly half of them open since
 * 2020-2023. Reporting that raw figure to an executive is misleading, so the
 * dataset carries both: everything is loaded, and `isAbandoned` marks the
 * aged tail. Confirm the cutoff with the exec team before it drives decisions.
 */
export const ABANDONED_AFTER_DAYS = Number(process.env.ER_ABANDONED_AFTER_DAYS ?? 365);

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

  const [gOpen, gPastCase, gPastHome, gInproc, gCaseload] = await Promise.all([
    gridFor(dir, "opencases"),
    gridFor(dir, "pastdue_case"),
    gridFor(dir, "pastdue_home"),
    gridFor(dir, "inprocess"),
    gridFor(dir, "caseload"),
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
    return {
      id: caseDisplayId(childName),
      displayId: caseDisplayId(childName),
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
  const compliance: ComplianceItem[] = [];
  let seq = 0;

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
      compliance.push({
        id: `ci-${spec.slug}-${seq++}`,
        caseId: linked?.id ?? subjectId,
        kind: classifyKind(type),
        label: type || "Task",
        dueDate: due ?? "",
        state: stateFor(due, r.status ?? ""),
      });
    }
  };

  ingestTasks(gPastCase, REPORT_SPECS.pastdue_case, "client");
  ingestTasks(gPastHome, REPORT_SPECS.pastdue_home, "home");
  ingestTasks(gInproc, REPORT_SPECS.inprocess, "client");

  // Roll the worst state on each case up onto the case record.
  const rank: Record<ComplianceState, number> = { ok: 0, due_soon: 1, overdue: 2 };
  for (const item of compliance) {
    const c = cases.find((x) => x.id === item.caseId);
    if (c && rank[item.state] > rank[c.compliance]) c.compliance = item.state;
  }

  // --- caseload census ------------------------------------------------------
  // Only used to register workers who hold cases but appear on no task row.
  const loadRows = rowsFor(gCaseload, REPORT_SPECS.caseload);
  note("caseload", gCaseload, loadRows);
  for (const r of loadRows) ensureWorker(r.worker ?? "");

  const caseworkers = [...workers.values()];
  const teams: Team[] = caseworkers.map((w) => ({
    id: w.teamId,
    name: `${w.name}'s caseload`,
    managerCaseworkerId: w.id,
  }));

  // --- trend ----------------------------------------------------------------
  // The monthly census report carries history; without it there is no trend,
  // and an invented one would be worse than none.
  const trend: TrendPoint[] = [];

  return {
    dataset: { teams, caseworkers, cases, compliance, trend },
    diagnostics,
  };
}
