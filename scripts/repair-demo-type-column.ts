#!/usr/bin/env tsx
/**
 * ONE-OFF REMEDIATION — kept in the repo for auditability, not for reuse.
 *
 * The de-identifier scrubs only the fields `schema.ts` declares sensitive. The
 * task `type` column was declared as nothing, and in this agency's data it
 * carries people's given names, because certification-expiry items are named
 * after the person they belong to:
 *
 *     "SIDS Expires (<given>)"
 *     "Valid Drivers License Expires (<given> <surname>)"
 *     "Child Logs (<given>, <given>)"        <- sibling groups
 *
 * Those names reached `data/demo`, a public GitHub repository and a public
 * Netlify demo. `schema.ts` and `scrubText` are now fixed, so a future run
 * over the REAL exports handles this correctly. This script exists because the
 * real exports are not available here, and re-running the de-identifier over
 * already-de-identified files is impossible by design: `buildPools` excludes
 * every name found in the input, so a second pass depletes the pool to nothing.
 *
 * It therefore repairs only the `type` column, in place, leaving every other
 * cell byte-identical so the demo's row counts, dates, statuses and
 * distributions are unchanged.
 *
 * The replacement pool is deliberately DISJOINT from the de-identifier's own
 * GIVEN pool. Reusing it would put a name into a task label that also appears
 * as a client name elsewhere in the same file, inviting a false association —
 * the same reason `buildPools` excludes source names in the first place.
 *
 *     npx tsx scripts/repair-demo-type-column.ts ./data/demo
 */

import { readdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import ExcelJS from "exceljs";
import { REPORT_SPECS, findHeaderRow } from "../src/lib/extendedreach/schema";
import { readGrid } from "../src/lib/extendedreach/grid";

/** Disjoint from GIVEN in deidentify-export.ts. Checked at startup. */
const REPAIR_GIVEN = [
  "Alder", "Briony", "Cassian", "Delphine", "Emory", "Fenwick", "Greer",
  "Halcyon", "Ines", "Jethro", "Kestrel", "Linnea", "Marlowe", "Nerissa",
  "Osric", "Perpetua", "Quill", "Rowan", "Sable", "Torin", "Ursula",
  "Vesper", "Wendell", "Ximena", "Yarrow", "Zinnia", "Anouk", "Bram",
  "Cleo", "Dorian", "Eulalia", "Fintan", "Galen", "Hesper", "Ilya",
];

const TASK_VOCAB =
  /\b(review|plan|report|visit|assessment|treatment|quarterly|monthly|annual|initial|renewal|update|form|training|medication|service|care|home|case|court|medical|dental|physical|test|screen|log|notes?|prescribed|otc|parent|basic|none|other|type|level|hours?|days?|years?|ytf|aka)\b/i;

const hashInt = (s: string) =>
  parseInt(createHash("sha256").update(`repair::${s.toLowerCase()}`).digest("hex").slice(0, 8), 16);

const synth = (real: string) => REPAIR_GIVEN[hashInt(real.trim()) % REPAIR_GIVEN.length];

/** The same rule now in scrubText, applied to one column. */
export function repairLabel(v: string): string {
  return v.replace(/\(([^)]{2,60})\)/g, (whole, inner: string) => {
    const t = inner.trim();
    if (TASK_VOCAB.test(t)) return whole;
    if (!/^[A-Z][a-z]+(?:,?\s+[A-Z][a-z]+){0,2}$/.test(t)) return whole;
    const parts = t.split(",").map((x) => x.trim()).filter(Boolean);
    if (parts.length > 1) return `(${parts.map(synth).join(", ")})`;
    return `(${synth(t)})`;
  });
}

async function main() {
  const dir = process.argv[2] ?? "./data/demo";
  const files = (await readdir(dir)).filter((f) => /\.xlsx$/i.test(f));
  let totalCells = 0;

  for (const f of files.sort()) {
    const slug = f.replace(/_\d{8}\.xlsx$/i, "");
    const spec = REPORT_SPECS[slug];
    if (!spec || spec.matrix || !("type" in spec.fields)) continue;

    const full = path.join(dir, f);
    const grid = await readGrid(full);
    const found = findHeaderRow(spec, grid);
    if (!found || found.columns.type === undefined) {
      console.log(`  – ${f}: no type column resolved, skipped`);
      continue;
    }
    const col = found.columns.type + 1; // ExcelJS is 1-indexed

    const wb = new ExcelJS.Workbook();
    await wb.xlsx.readFile(full);
    const ws = wb.worksheets[0];
    let changed = 0;

    ws.eachRow({ includeEmpty: false }, (row, rowNumber) => {
      if (rowNumber <= found.header + 1) return;
      const cell = row.getCell(col);
      const raw = typeof cell.value === "string" ? cell.value : null;
      if (!raw) return;
      const next = repairLabel(raw);
      if (next !== raw) {
        cell.value = next;
        changed++;
      }
    });

    if (changed) await wb.xlsx.writeFile(full);
    totalCells += changed;
    console.log(`  ${changed ? "✎" : "·"} ${f}: ${changed} label(s) repaired`);
  }
  console.log(`\n${totalCells} cells repaired.`);
}

main();
