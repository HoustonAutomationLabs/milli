#!/usr/bin/env tsx
/**
 * Reconcile a real ExtendedReach export against what the loader expects.
 *
 * The column names in `src/lib/extendedreach/schema.ts` are the audit's best
 * reading of each report, taken from the rendered screen. Exported header text
 * does not always match. Without this tool the only symptom of a mismatch is
 * "zero rows", which says nothing about the cause.
 *
 * Point it at a workbook and it reports which fields resolved, which did not,
 * what headers are actually present, and the exact alias line to add.
 *
 *   npm run inspect:export -- ./data/exports/pastdue_case_20260822.xlsx
 *   npm run inspect:export -- ./data/exports            # whole directory
 *   npm run inspect:export -- <file> --slug pastdue_case
 *
 * PHI SAFETY
 * ----------
 * Output is safe to paste into a chat or ticket. Values from free-text and
 * name-bearing columns are masked to their shape ("Xxxx, Xxxxx"); only
 * categorical columns (status, type, program) and dates are shown verbatim.
 * `--unmask` exists for local debugging and prints a warning; never use it for
 * output you intend to share.
 */

import { readdir } from "node:fs/promises";
import { statSync } from "node:fs";
import path from "node:path";
import process from "node:process";

import { isReadableExport, readGrid } from "../src/lib/extendedreach/grid";
import {
  MATRIX_SPECS,
  REPORT_SPECS,
  findHeaderRow,
  findMatrixHeader,
  normaliseHeader,
  parseMatrixCell,
  resolveColumns,
  type MatrixReportSpec,
  type ReportSpec,
} from "../src/lib/extendedreach/schema";

const args = process.argv.slice(2);
const flag = (n: string) => args.includes(`--${n}`);
const opt = (n: string) => {
  const i = args.indexOf(`--${n}`);
  return i >= 0 ? args[i + 1] : undefined;
};
const targets = args.filter((a) => !a.startsWith("--") && args[args.indexOf(a) - 1] !== "--slug");

const UNMASK = flag("unmask");

/** Fields whose values are categorical, not personal — safe to print. */
const SAFE_FIELDS = new Set([
  "status", "type", "program", "requirement", "licenseType",
  "month", "dueDate", "date", "expiresOn", "courtDate", "openedOn",
  "activeCases", "onTimePct", "avgVariance", "bedsAvailable", "placementType",
]);

const C = {
  dim: (s: string) => `\x1b[2m${s}\x1b[0m`,
  bold: (s: string) => `\x1b[1m${s}\x1b[0m`,
  green: (s: string) => `\x1b[32m${s}\x1b[0m`,
  red: (s: string) => `\x1b[31m${s}\x1b[0m`,
  yellow: (s: string) => `\x1b[33m${s}\x1b[0m`,
  cyan: (s: string) => `\x1b[36m${s}\x1b[0m`,
};

/** Reduce a value to its shape so structure is visible but content is not. */
function mask(v: string): string {
  if (!v) return "";
  return v.replace(/[A-Za-z]/g, (ch) => (ch === ch.toUpperCase() ? "X" : "x")).replace(/\d/g, "#");
}

function show(field: string | null, value: string): string {
  if (UNMASK) return value;
  if (field && SAFE_FIELDS.has(field)) return value;
  return mask(value);
}

/**
 * Rank unclaimed headers as candidates for a field, by token overlap with the
 * aliases already listed for it. "Task Due" shares "due" with the dueDate
 * aliases; "Obligation Name" shares "obligation" with the type aliases. This
 * turns a list of every spare column into a specific, usually-correct guess.
 */
function suggestAssignments(
  fieldAliases: Record<string, string[]>,
  fields: string[],
  unclaimed: string[],
): Record<string, string[]> {
  const tokens = (s: string) => new Set(normaliseHeader(s).split(/[^a-z0-9%]+/).filter(Boolean));

  // Score every field/header pair.
  const pairs: { field: string; header: string; score: number }[] = [];
  for (const field of fields) {
    for (const header of unclaimed) {
      const ht = tokens(header);
      let best = 0;
      for (const alias of fieldAliases[field] ?? []) {
        const at = tokens(alias);
        if (!at.size) continue;
        let shared = 0;
        for (const t of at) if (ht.has(t)) shared++;
        // Longer aliases matching in full are stronger evidence than a single
        // generic word, so weight by alias length.
        best = Math.max(best, (shared / at.size) * (1 + 0.25 * (at.size - 1)));
      }
      if (best > 0) pairs.push({ field, header, score: best });
    }
  }

  // Greedy one-to-one assignment: a header suggested for one field is not
  // offered as the top pick for another.
  pairs.sort((a, b) => b.score - a.score);
  const out: Record<string, string[]> = Object.fromEntries(fields.map((f) => [f, []]));
  const takenHeader = new Set<string>();
  const takenField = new Set<string>();
  for (const p of pairs) {
    if (takenHeader.has(p.header) || takenField.has(p.field)) continue;
    out[p.field].push(p.header);
    takenHeader.add(p.header);
    takenField.add(p.field);
  }
  // Any remaining plausible options listed as alternates.
  for (const p of pairs) {
    if (!out[p.field].includes(p.header) && out[p.field].length < 3) out[p.field].push(p.header);
  }
  return out;
}

/**
 * Does this row read as column labels rather than records?
 *
 * Reconciliation needs the header text verbatim — masking it defeats the
 * point, and a column label is metadata, not PHI. Data rows are a different
 * matter, so rather than guessing cell by cell we only ever print rows that
 * look like labels, and drop record rows entirely.
 *
 * Labels are short, free of digits, and not in "Last, First" form.
 */
function looksLikeLabels(row: string[]): boolean {
  const cells = row.filter(Boolean);
  if (cells.length < 2) return false;
  const labelish = cells.filter(
    (c) => c.length <= 40 && !/\d/.test(c) && !/^[A-Z][\w'-]*,\s/.test(c),
  );
  return labelish.length / cells.length >= 0.8;
}

/** Does this filename identify itself as belonging to `slug`? */
function matchesSlug(base: string, slug: string): boolean {
  return base.startsWith(`${slug}_`) || base === `${slug}.xlsx` || base === `${slug}.csv`;
}

function specForFile(file: string): ReportSpec | MatrixReportSpec | null {
  const forced = opt("slug");
  if (forced) return REPORT_SPECS[forced] ?? MATRIX_SPECS[forced] ?? null;
  const base = path.basename(file);
  return (
    Object.values(REPORT_SPECS).find((s) => matchesSlug(base, s.slug)) ??
    Object.values(MATRIX_SPECS).find((s) => matchesSlug(base, s.slug)) ??
    null
  );
}

/** Matrix specs carry `idFields`; list specs carry `fields`. */
function isMatrix(spec: ReportSpec | MatrixReportSpec): spec is MatrixReportSpec {
  return "idFields" in spec;
}

/**
 * Reconcile a matrix report.
 *
 * There is no fixed column list to check off, so "did this resolve" means
 * something different here: the identity block must resolve, every cell must
 * parse into a known form, and the obligation columns are reported as a count
 * plus a sample. An unparsed cell is the failure mode that matters — it means
 * ExtendedReach has a status word the loader would silently miscategorise.
 */
function inspectMatrix(spec: MatrixReportSpec, grid: string[][]): boolean {
  const layout = findMatrixHeader(spec, grid);
  if (!layout) {
    console.log("\n" + C.red("  ✖ MISMATCH — no header row resolves the identity columns."));
    console.log(C.dim(`    Required: ${spec.required.join(", ")}`));
    console.log(C.dim(`    Known aliases: ${JSON.stringify(spec.idFields)}`));
    return false;
  }

  console.log(C.dim(`  header row ${layout.header}`));
  console.log("\n" + C.bold("  Identity columns"));
  for (const [field, col] of Object.entries(layout.id)) {
    console.log(`    ${C.green("✓")} ${field.padEnd(18)} col ${String(col).padStart(2)}  ${C.cyan(grid[layout.header][col])}`);
  }
  const unresolved = Object.keys(spec.idFields).filter((f) => !(f in layout.id));
  for (const f of unresolved) console.log(`    ${C.yellow("·")} ${f.padEnd(18)} ${C.dim("not present")}`);

  // Obligation labels are Configurator item names — metadata, not PHI.
  console.log("\n" + C.bold(`  Obligation columns: ${layout.items.length}`));
  console.log(C.dim(`    ${layout.items.slice(0, 8).map((i) => i.label).join(" | ")}${layout.items.length > 8 ? " | …" : ""}`));

  // Cell vocabulary. Dates are reduced to <date> so nothing identifies a case.
  const states = new Map<string, number>();
  const unknown = new Map<string, number>();
  let rows = 0;
  for (let r = layout.header + 1; r < grid.length; r++) {
    const row = grid[r] ?? [];
    if (row.every((c) => !c)) continue;
    if (spec.required.every((f) => !row[layout.id[f]])) continue;
    rows++;
    for (const item of layout.items) {
      const raw = row[item.col] ?? "";
      const cell = parseMatrixCell(raw);
      const shape = raw.trim()
        ? raw.trim().replace(/\d{1,2}\/\d{1,2}\/\d{4}/, "<date>")
        : "(blank)";
      states.set(`${cell.state}`, (states.get(`${cell.state}`) ?? 0) + 1);
      // A dated cell with an unrecognised flag, or an undated non-keyword,
      // is a form the parser does not know.
      if (!cell.date && cell.marker && !/^(optional|missing)$/i.test(cell.marker)) {
        unknown.set(shape, (unknown.get(shape) ?? 0) + 1);
      } else if (cell.date && cell.state === "not_applicable") {
        unknown.set(shape, (unknown.get(shape) ?? 0) + 1);
      }
    }
  }

  console.log("\n" + C.bold(`  Cells parsed: ${rows} rows × ${layout.items.length} obligations`));
  for (const [state, n] of [...states.entries()].sort((a, b) => b[1] - a[1])) {
    console.log(`    ${state.padEnd(16)} ${String(n).padStart(5)}`);
  }

  if (unknown.size) {
    console.log("\n" + C.red(`  ✖ ${unknown.size} unrecognised cell form(s) — add them to parseMatrixCell:`));
    for (const [shape, n] of [...unknown.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12)) {
      console.log(`    ${C.yellow(shape)} ${C.dim(`× ${n}`)}`);
    }
    return false;
  }

  console.log("\n  " + C.bold("Would parse: ") + C.green(`${rows} rows`) + C.dim(" · every cell recognised"));
  return rows > 0;
}

async function inspect(file: string): Promise<boolean> {
  const base = path.basename(file);
  console.log("\n" + C.bold("━".repeat(72)));
  console.log(C.bold(base));

  const spec = specForFile(file);
  if (!spec) {
    console.log(C.red("  ✖ No matching report spec."));
    console.log(C.dim(`    Filename must start with a known slug, or pass --slug <name>.`));
    console.log(
      C.dim(`    Known: ${[...Object.keys(REPORT_SPECS), ...Object.keys(MATRIX_SPECS)].join(", ")}`),
    );
    return false;
  }
  console.log(C.dim(`${spec.label}  ·  ${spec.view}  ·  slug: ${spec.slug}`));

  const grid = await readGrid(file);
  if (!grid.length) {
    console.log(C.red("  ✖ File is empty or unreadable."));
    return false;
  }
  console.log(C.dim(`${grid.length} rows read`));

  if (isMatrix(spec)) return inspectMatrix(spec, grid);

  const found = findHeaderRow(spec, grid);

  if (!found) {
    console.log("\n" + C.red("  ✖ MISMATCH — no header row resolves the required fields."));
    console.log(C.dim(`    Required: ${spec.required.join(", ")}\n`));
    console.log(C.bold("  Label rows found in the file:"));
    let shown = 0;
    for (let r = 0; r < Math.min(grid.length, 10); r++) {
      const cells = grid[r].filter(Boolean);
      if (!cells.length || !looksLikeLabels(grid[r])) continue;
      shown++;
      const { columns } = resolveColumns(spec, grid[r]);
      const marks = Object.keys(columns).length;
      // Column labels print verbatim — they are metadata, not PHI.
      console.log(`    row ${r}: ${C.cyan(cells.join(" | "))}`);
      console.log(
        C.dim(
          marks
            ? `             ↑ resolves ${marks} field(s): ${Object.keys(columns).join(", ")}`
            : `             ↑ resolves nothing`,
        ),
      );
    }
    if (!shown) {
      console.log(C.dim("    (none — the file may have no header row, or start straight into data)"));
    }

    // Name the gap concretely rather than leaving them to diff it by eye.
    const best = grid
      .slice(0, 10)
      .map((row, r) => ({ r, row, n: Object.keys(resolveColumns(spec, row).columns).length }))
      .filter((x) => looksLikeLabels(x.row))
      .sort((a, b) => b.n - a.n)[0];

    if (best) {
      const { columns } = resolveColumns(spec, best.row);
      const stillMissing = spec.required.filter((f) => !(f in columns));
      const unclaimed = best.row.filter(
        (h, i) => h && !Object.values(columns).includes(i),
      );
      if (stillMissing.length && unclaimed.length) {
        console.log("\n  " + C.bold(`Required field(s) with no column: `) + C.red(stillMissing.join(", ")));
        console.log("  " + C.bold("Unclaimed columns on row ") + best.r + ": " + C.cyan(unclaimed.join(", ")));
        console.log("\n  " + C.yellow("Likely fix — add to REPORT_SPECS." + spec.slug + ".fields in schema.ts:"));
        const suggestions = suggestAssignments(spec.fields, stillMissing, unclaimed);
        for (const f of stillMissing) {
          const ranked = suggestions[f] ?? [];
          if (ranked.length) {
            console.log(
              C.dim(`      ${f}: [..., ${JSON.stringify(normaliseHeader(ranked[0]))}],`) +
                (ranked.length > 1 ? C.dim(`   // or: ${ranked.slice(1, 3).map((r) => `"${normaliseHeader(r)}"`).join(", ")}`) : ""),
            );
          } else {
            console.log(
              C.dim(`      ${f}: [..., "?"]  `) +
                C.yellow(`no obvious candidate — pick from: ${unclaimed.join(", ")}`),
            );
          }
        }
      }
    }
    console.log("\n" + C.yellow("  Fix: add the real header text to the field's alias list in"));
    console.log(C.yellow("       src/lib/extendedreach/schema.ts, then re-run."));
    return false;
  }

  console.log(C.green(`\n  ✓ Header found at row ${found.header}`));

  // Resolved fields
  console.log("\n  " + C.bold("Resolved fields"));
  for (const [field, idx] of Object.entries(found.columns)) {
    const header = grid[found.header][idx];
    const sample = grid.slice(found.header + 1).find((r) => r[idx])?.[idx] ?? "";
    const req = spec.required.includes(field) ? C.dim(" (required)") : "";
    console.log(
      `    ${C.green("✓")} ${field.padEnd(15)} ${C.dim("←")} "${header}"${req}` +
        (sample ? C.dim(`   e.g. ${show(field, sample)}`) : ""),
    );
  }

  // Unresolved fields, with suggestions
  if (found.missing.length) {
    const usedIdx = new Set(Object.values(found.columns));
    const spare = grid[found.header]
      .map((h, i) => ({ h, i }))
      .filter(({ h, i }) => h && !usedIdx.has(i));

    console.log("\n  " + C.bold("Unresolved fields") + C.dim(" (optional unless marked required)"));
    for (const field of found.missing) {
      const req = spec.required.includes(field) ? C.red(" (REQUIRED)") : "";
      console.log(`    ${C.yellow("○")} ${field}${req}`);
    }
    if (spare.length) {
      console.log("\n  " + C.bold("Columns in the file that nothing claimed"));
      for (const { h } of spare) console.log(`    ${C.cyan(`"${h}"`)}`);
      console.log("\n  " + C.yellow("If one of these is a field above, add it to schema.ts:"));
      const guess = found.missing[0];
      console.log(
        C.dim(`      ${guess}: [..., ${JSON.stringify(normaliseHeader(spare[0].h))}],`),
      );
    }
  }

  // How many rows would actually parse
  let parsed = 0;
  for (let r = found.header + 1; r < grid.length; r++) {
    const row = grid[r];
    if (!row || row.every((c) => !c)) continue;
    const obj: Record<string, string> = {};
    for (const [f, i] of Object.entries(found.columns)) obj[f] = row[i] ?? "";
    if (spec.required.every((f) => !obj[f])) continue;
    parsed++;
  }
  const skipped = grid.length - found.header - 1 - parsed;
  console.log(
    "\n  " +
      C.bold("Would parse: ") +
      (parsed > 0 ? C.green(`${parsed} rows`) : C.red("0 rows")) +
      C.dim(`   (${skipped} skipped as blank or grouping rows)`),
  );

  return parsed > 0 && !spec.required.some((f) => found.missing.includes(f));
}

async function main() {
  if (!targets.length) {
    console.log("Usage: npm run inspect:export -- <file.xlsx|.csv | directory> [--slug <name>] [--unmask]");
    process.exit(1);
  }
  if (UNMASK) {
    console.log(C.red("\n⚠ --unmask prints real values, including children's names."));
    console.log(C.red("  Do not share this output.\n"));
  }

  const files: string[] = [];
  for (const t of targets) {
    if (statSync(t).isDirectory()) {
      const entries = await readdir(t);
      files.push(...entries.filter(isReadableExport).map((f) => path.join(t, f)));
    } else {
      files.push(t);
    }
  }

  if (!files.length) {
    console.log("No .xlsx or .csv files found.");
    process.exit(1);
  }

  const results: boolean[] = [];
  for (const f of files.sort()) results.push(await inspect(f));

  const ok = results.filter(Boolean).length;
  console.log("\n" + C.bold("━".repeat(72)));
  console.log(C.bold(`${ok}/${results.length} report(s) ready for the loader.`));
  if (ok < results.length) {
    console.log(C.yellow("Fix the mismatches above in src/lib/extendedreach/schema.ts, then re-run."));
    process.exit(2);
  }
  console.log(C.green("Set DATA_SOURCE=exports to use them."));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
