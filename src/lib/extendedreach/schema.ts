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
      worker: ["worker", "case manager", "caseworker", "assigned to", "performer"],
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
