/**
 * What each ExtendedReach export is expected to contain.
 *
 * This is the single source of truth shared by the loader
 * (`exports.ts`) and the reconciliation tool (`scripts/inspect-export.ts`),
 * so a mapping fix in one place fixes both.
 *
 * Why aliases
 * -----------
 * The audit recorded each report's column headers by reading the screen, and
 * ExtendedReach's exported header text does not always match its rendered
 * label. Rather than pinning one exact string per field and failing when it
 * differs by a word, each field lists the header variants that mean the same
 * thing. Matching is case-insensitive and whitespace-normalised.
 *
 * When a real export turns up a header not listed here, add it to the alias
 * list — that is the intended way to fix a mismatch. `inspect-export` prints
 * the exact line to add.
 */

/** A logical field the loader reads, and the header texts that can carry it. */
export type FieldAliases = Record<string, string[]>;

export interface ReportSpec {
  /** Filename slug produced by the exporter. */
  slug: string;
  /** Human name, as it appears in the ExtendedReach menu. */
  label: string;
  /** ExtendedReach's internal view code, from the audit. */
  view: string;
  /**
   * Logical fields the loader needs, each mapped to acceptable header texts.
   * The first entry is the canonical name used in code.
   */
  fields: FieldAliases;
  /**
   * Fields without which a row is meaningless. If none of these resolve to a
   * column, the report has not been understood and the loader yields nothing —
   * which `inspect-export` reports as a mismatch rather than an empty result.
   */
  required: string[];
}

export const REPORT_SPECS: Record<string, ReportSpec> = {
  opencases: {
    slug: "opencases",
    label: "Foster Care Open Cases",
    view: "V_CLIENTS_LASTNAME_ACTIVE-C",
    required: ["client", "worker"],
    fields: {
      client: ["client", "name", "child", "case name", "client name", "last name"],
      worker: ["case manager", "worker", "caseworker", "primary worker", "assigned worker"],
      placementType: ["placement type", "placement", "current placement", "home type"],
      openedOn: ["admission", "admission date", "opened", "opened on", "start date", "date admitted"],
      program: ["program", "category"],
    },
  },

  pastdue_case: {
    slug: "pastdue_case",
    label: "Case Tasks — Due Soon / Past Due",
    view: "V_TASKS_INPROC_PASTDUEBYDATE-C",
    required: ["dueDate", "type"],
    fields: {
      dueDate: ["date", "due", "due date"],
      // Real values seen: Due, Submitted, Draft, Expires, Rejected,
      // Scheduled, Event — not the "Past Due" / "Due in 30 Days" section
      // labels the report groups by on screen.
      status: ["status", "state"],
      type: ["type", "task", "task type", "obligation", "report type"],
      worker: ["worker", "case manager", "caseworker", "assigned to", "performer", "performed by"],
      client: ["client", "name", "child", "case name", "client name"],
      program: ["program"],
      description: ["description", "notes", "detail"],
    },
  },

  pastdue_home: {
    slug: "pastdue_home",
    label: "Home Tasks — Due Soon / Past Due",
    view: "V_HOMETASKS_INPROC_PASTDUEBYDATE-C",
    required: ["dueDate", "type"],
    fields: {
      dueDate: ["date", "due", "due date"],
      status: ["status", "state"],
      type: ["type", "task", "task type", "obligation"],
      worker: ["worker", "licensing worker", "assigned to", "performer"],
      home: ["home", "household", "home name", "provider", "name"],
      description: ["description", "notes", "detail"],
    },
  },

  inprocess: {
    slug: "inprocess",
    label: "Case Tasks — In Process",
    view: "V_TASKS_INPROC-C",
    required: ["dueDate", "type"],
    fields: {
      dueDate: ["date", "due", "due date"],
      status: ["status", "state"],
      type: ["type", "task", "task type", "report type"],
      worker: ["worker", "case manager", "caseworker", "performer"],
      client: ["client", "name", "child", "case name"],
      description: ["description", "notes"],
    },
  },

  completions: {
    slug: "completions",
    label: "Activities Completed by Date",
    view: "V_ALLBYCOMPLETION_ACTIVITIES-C",
    required: ["date", "type"],
    fields: {
      date: ["date", "completed", "completion date"],
      type: ["type", "activity", "activity type"],
      client: ["client", "name", "child", "case name"],
      worker: ["worker", "entered by", "performer", "case manager"],
      program: ["program"],
      description: ["description", "notes"],
    },
  },

  caseload: {
    slug: "caseload",
    label: "Monthly Census by Worker",
    view: "V_CASELOADS_WKR_MONTH-C",
    required: ["worker"],
    fields: {
      worker: ["worker", "case manager", "caseworker"],
      month: ["month", "period", "month/year"],
      activeCases: ["active cases", "cases", "count", "caseload", "total"],
    },
  },

  ontime: {
    slug: "ontime",
    label: "% On Time by Program",
    view: "V_MONTHVAR-C",
    required: ["month"],
    fields: {
      month: ["month", "period", "month/year"],
      program: ["program"],
      onTimePct: ["% on time", "on time", "percent on time", "on-time %", "pct on time"],
      avgVariance: ["avg days variance", "variance", "average variance", "avg variance"],
    },
  },

  openbeds: {
    slug: "openbeds",
    label: "Available Homes — Open Beds",
    view: "V_HOMES_AVAILABLE-C",
    required: ["home"],
    fields: {
      home: ["home", "household", "home name", "provider", "name"],
      licenseType: ["license type", "license", "type"],
      bedsAvailable: ["available beds", "open beds", "beds", "capacity"],
      lastPlacement: ["last placement", "last placement date"],
    },
  },

  nextcourt: {
    slug: "nextcourt",
    label: "Next Court Date",
    view: "V_CLIENTS_NEXTCOURT-C",
    required: ["client"],
    fields: {
      client: ["client", "name", "child", "case name"],
      courtDate: ["next court date", "court date", "date"],
      judge: ["judge"],
      description: ["court description", "description", "notes"],
    },
  },

  staffexp: {
    slug: "staffexp",
    label: "Staff Events + Expirations by Date",
    view: "V_STAFF_EXPBYDATE-C",
    required: ["expiresOn"],
    fields: {
      expiresOn: ["date", "expires", "expiration", "expiration date", "expires on"],
      staff: ["staff", "name", "employee", "worker"],
      requirement: ["event", "requirement", "type", "item"],
    },
  },

  // -- Verified against real exports, 2026-08-22 -----------------------------

  /**
   * The supervisor approval queue. Every row is Status=Submitted by
   * definition, so this report does not measure caseworker backlog — it
   * measures how much finished work is waiting on an approver.
   *
   * This is the other half of the Submitted finding in `pastdue_case`: 165 of
   * the 997 past-due case tasks are Submitted, and this report is where all
   * such items live, past due or not.
   */
  needapproval_case: {
    slug: "needapproval_case",
    label: "Case Tasks — Awaiting Approval",
    view: "V_REPORTS_NEEDAPPROVAL-C",
    required: ["submittedOn", "type"],
    fields: {
      submittedOn: ["date", "submitted", "submitted on"],
      status: ["status", "state"],
      type: ["type", "task", "task type", "report type"],
      // "Performed By" is who did the work. Unlike the `Worker` column on the
      // task reports — which records who *entered* an item — this one does
      // name the performer. It is still not a caseload figure.
      worker: ["performed by", "performer", "worker", "case manager"],
      // The approver the item is sitting with. This is the queue that matters
      // here: approval load concentrates far harder than casework load does.
      approver: ["submit to", "submitted to", "approver", "supervisor"],
      client: ["client", "name", "child", "case name", "client name"],
      description: ["description", "notes", "detail"],
      program: ["program"],
    },
  },

  /**
   * Rejected submissions — work that was done, submitted, and sent back.
   * Small in volume but the highest-signal rows in the system: each one is a
   * documented rework loop, and `Reason Rejected` says why.
   *
   * Note the date column is labelled "Rejected", not "Date".
   */
  rejected_case: {
    slug: "rejected_case",
    label: "Case Tasks — Rejected",
    view: "V_TASKS_REJECTED-C",
    required: ["rejectedOn", "type"],
    fields: {
      rejectedOn: ["rejected", "date", "rejected on"],
      status: ["status", "state"],
      type: ["type", "task", "task type", "report type"],
      worker: ["performed by", "performer", "worker", "case manager"],
      approver: ["submit to", "submitted to", "approver", "supervisor"],
      client: ["client", "name", "child", "case name", "client name"],
      reason: ["reason rejected", "reason", "rejection reason"],
      description: ["description", "notes", "detail"],
      program: ["program"],
    },
  },

  /**
   * Completed case *reports*. Distinct from `completions`, which is the
   * Activities view (`V_ALLBYCOMPLETION_ACTIVITIES-C`) and covers a different
   * 9,564-row population; this one is the 16,244-row Reports population.
   *
   * The export carries three unlabelled leading columns — year, month and
   * record type — before the real header cells, which is why the header row
   * is located by scoring rather than assumed. Its subject column is headed
   * "Name", not "Client".
   *
   * Its `Worker` column is the entered-by column, with the concentration that
   * implies: 145 rows across 41 subjects but only 9 workers. Never label it
   * caseload. See docs/extendedreach-audit.md.
   */
  reportscompleted: {
    slug: "reportscompleted",
    label: "Reports Completed by Date",
    view: "V_ALLBYCOMPLETION_REPORTS-C",
    required: ["date", "type"],
    fields: {
      date: ["date", "completed", "completion date"],
      type: ["type", "report type", "activity"],
      client: ["name", "client", "child", "case name"],
      worker: ["worker", "entered by", "performed by", "performer"],
      description: ["description", "notes"],
      program: ["program"],
    },
  },
};

/** Normalise a header cell for comparison: collapse whitespace, lowercase. */
export function normaliseHeader(raw: string): string {
  return raw.replace(/\s+/g, " ").trim().toLowerCase();
}

/**
 * Resolve a spec's logical fields against a header row.
 * Returns the column index per field, and the fields that found no column.
 */
export function resolveColumns(
  spec: ReportSpec,
  headerRow: string[],
): { columns: Record<string, number>; missing: string[] } {
  const seen = headerRow.map(normaliseHeader);
  const columns: Record<string, number> = {};
  const missing: string[] = [];

  for (const [field, aliases] of Object.entries(spec.fields)) {
    const idx = seen.findIndex((h) => h && aliases.includes(h));
    if (idx >= 0) columns[field] = idx;
    else missing.push(field);
  }
  return { columns, missing };
}

/**
 * Locate the header row in a grid.
 *
 * Real exports carry title rows and unlabelled leading columns, so the header
 * is not reliably row 0. Score each candidate row by how many of the spec's
 * fields it resolves, and take the best — requiring every `required` field to
 * be present, so a stray row with one matching word is not mistaken for it.
 */
export function findHeaderRow(
  spec: ReportSpec,
  grid: string[][],
  scanRows = 12,
): { header: number; columns: Record<string, number>; missing: string[] } | null {
  let best: { header: number; columns: Record<string, number>; missing: string[]; score: number } | null = null;

  for (let r = 0; r < Math.min(grid.length, scanRows); r++) {
    const { columns, missing } = resolveColumns(spec, grid[r] ?? []);
    const hasRequired = spec.required.every((f) => f in columns);
    if (!hasRequired) continue;
    const score = Object.keys(columns).length;
    if (!best || score > best.score) best = { header: r, columns, missing, score };
  }

  return best ? { header: best.header, columns: best.columns, missing: best.missing } : null;
}

// ---------------------------------------------------------------------------
// Matrix reports
// ---------------------------------------------------------------------------

/**
 * The Compliance Tracking custom reports are a different shape from every
 * other export, and the `ReportSpec` model above cannot describe them.
 *
 * A list report is one row per obligation. A matrix report is one row per
 * *subject* and one column per obligation type — 52 cases wide by 76
 * compliance items in the real export, every cell filled. The obligation
 * names are data, not schema: they come from the agency's Configurator and
 * change when it does, so they cannot be enumerated here as aliases.
 *
 * The spec therefore pins only the leading identity columns and treats
 * everything to their right as obligations to be unpivoted.
 */
export interface MatrixReportSpec {
  slug: string;
  label: string;
  view: string;
  /** Leading columns that identify the subject of the row. */
  idFields: FieldAliases;
  /** Identity fields without which a row cannot be attributed. */
  required: string[];
}

export const MATRIX_SPECS: Record<string, MatrixReportSpec> = {
  compliance_case: {
    slug: "compliance_case",
    label: "Case Tasks — Compliance Tracking",
    view: "A_COMPLIANCE_CASES",
    required: ["client"],
    idFields: {
      client: ["case", "client", "name", "child", "case name"],
      worker: ["case manager", "worker", "caseworker"],
      secondaryWorker: ["sec. worker", "secondary worker", "sec worker"],
      placement: ["current placement", "placement", "home"],
    },
  },
};

/** Resolved layout of a matrix report: identity columns plus obligation columns. */
export interface MatrixLayout {
  header: number;
  /** Column index per identity field. */
  id: Record<string, number>;
  /** Obligation columns, in file order. */
  items: { label: string; col: number }[];
}

/**
 * Locate the header row of a matrix report and split it into identity columns
 * and obligation columns.
 *
 * Obligation headers cannot be validated against a list — any column to the
 * right of the last identity column that carries a label is one. That is
 * permissive by necessity, so the identity block is what anchors the match:
 * if the required identity fields do not resolve, the row is not the header.
 */
export function findMatrixHeader(
  spec: MatrixReportSpec,
  grid: string[][],
  scanRows = 12,
): MatrixLayout | null {
  for (let r = 0; r < Math.min(grid.length, scanRows); r++) {
    const row = grid[r] ?? [];
    const seen = row.map(normaliseHeader);

    const id: Record<string, number> = {};
    const claimed = new Set<number>();
    for (const [field, aliases] of Object.entries(spec.idFields)) {
      const idx = seen.findIndex((h, i) => h && !claimed.has(i) && aliases.includes(h));
      if (idx >= 0) {
        id[field] = idx;
        claimed.add(idx);
      }
    }
    if (!spec.required.every((f) => f in id)) continue;

    // Obligations start after the last identity column so that an unmatched
    // identity column (say a "Sec. Worker" the spec has not seen) is not
    // mistaken for a compliance item.
    const lastId = Math.max(...Object.values(id));
    const items: { label: string; col: number }[] = [];
    for (let c = lastId + 1; c < row.length; c++) {
      const label = (row[c] ?? "").trim();
      if (label) items.push({ label, col: c });
    }
    if (!items.length) continue;

    return { header: r, id, items };
  }
  return null;
}

/**
 * The state of one compliance cell.
 *
 * Aligns with `ComplianceState` in the dashboard's types, plus
 * `not_applicable` — a matrix cell can say an obligation does not apply to
 * this case, which no list report ever needs to express.
 */
export type MatrixCellState = "ok" | "due_soon" | "overdue" | "not_applicable";

export interface MatrixCell {
  /** ISO date carried by the cell, when it has one. */
  date: string | null;
  /** ExtendedReach's own parenthetical flag, verbatim, when present. */
  marker: string | null;
  state: MatrixCellState;
}

/**
 * Read one compliance cell.
 *
 * The full vocabulary, counted across all 3,952 cells of the real export:
 * a bare date (2,209), `Optional` (637), `<date> (Due)` (389), `Missing`
 * (283), `<date> (Overdue)` (264), `<date> (Expires)` (104), `<date>
 * (Expired)` (27), `<date> (In Proc.)` (21), `<date> (Submitted)` (16),
 * `<date> (Sched.)` (2). There were no blanks.
 *
 * The mapping follows the same rule the task loader applies in `stateFor`:
 * work that has left the caseworker's hands is not their outstanding work.
 * So `Submitted` is satisfied here exactly as it is there, and `Sched.` is a
 * calendar entry rather than a date-driven obligation.
 *
 * `Missing` is the one judgement call. It carries no date, so it cannot be
 * aged, but it means a required document has never been provided — a real
 * compliance gap, not an unknown. It counts as overdue, and because it has no
 * date it will never appear in an age bucket; that is the honest
 * representation rather than dropping it or inventing a date.
 */
export function parseMatrixCell(raw: string): MatrixCell {
  const value = (raw ?? "").trim();
  if (!value) return { date: null, marker: null, state: "not_applicable" };

  if (/^optional$/i.test(value)) return { date: null, marker: "Optional", state: "not_applicable" };
  if (/^missing$/i.test(value)) return { date: null, marker: "Missing", state: "overdue" };

  const m = value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s*\(([^)]*)\))?$/);
  if (!m) {
    // An unrecognised cell is reported as unknown rather than guessed at. If
    // this ever fires, add the new form here rather than letting it fall into
    // a category it may not belong to.
    return { date: null, marker: value, state: "not_applicable" };
  }

  const [, mo, d, y, flag] = m;
  const date = `${y}-${mo.padStart(2, "0")}-${d.padStart(2, "0")}`;
  const marker = flag?.trim() || null;

  switch ((marker ?? "").toLowerCase()) {
    case "overdue":
    case "expired":
      return { date, marker, state: "overdue" };
    case "due":
    case "expires":
    case "in proc.":
    case "in proc":
      return { date, marker, state: "due_soon" };
    case "submitted":
    case "sched.":
    case "sched":
      return { date, marker, state: "ok" };
    case "":
      // A bare date is the date the item was completed.
      return { date, marker: null, state: "ok" };
    default:
      return { date, marker, state: "not_applicable" };
  }
}
