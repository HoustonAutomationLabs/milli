#!/usr/bin/env tsx
/**
 * Split a combined ExtendedReach workbook into the per-slug files the loader
 * and `inspect-export` expect.
 *
 * The Playwright exporter (`export-extendedreach.mjs`) writes one file per
 * report, named `<slug>_YYYYMMDD.<ext>` — that convention is what
 * `exports.ts` and `inspect-export.ts` key on. A separate scheduled pull
 * (outside this repo) instead produces a single workbook named
 * `ExtendedReach_Reports_<timestamp>.xlsx` with one sheet per report, sheet
 * name equal to the report's slug. This script bridges the two shapes so
 * that a combined workbook can be dropped into `data/exports` and everything
 * downstream — `inspect:export`, `DATA_SOURCE=exports`, `deidentify` — works
 * unchanged.
 *
 *   npm run split:workbook -- ./data/exports/ExtendedReach_Reports_2026-09-01_2359.xlsx
 *   npm run split:workbook -- <file> --out ./data/exports
 *
 * A sheet whose name is not a known report slug is skipped and named in the
 * summary rather than guessed at.
 */

import path from "node:path";
import process from "node:process";
import ExcelJS from "exceljs";

import { REPORT_SPECS, MATRIX_SPECS } from "../src/lib/extendedreach/schema";

const args = process.argv.slice(2);
const opt = (n: string) => {
  const i = args.indexOf(`--${n}`);
  return i >= 0 ? args[i + 1] : undefined;
};
const input = args.find((a) => !a.startsWith("--") && args[args.indexOf(a) - 1] !== "--out");
const outDir = opt("out") ?? (input ? path.dirname(input) : "./data/exports");

if (!input) {
  console.log("Usage: npm run split:workbook -- <combined-workbook.xlsx> [--out <dir>]");
  process.exit(1);
}

const KNOWN_SLUGS = new Set([
  ...Object.keys(REPORT_SPECS),
  ...Object.keys(MATRIX_SPECS),
]);

async function main() {
  const src = new ExcelJS.Workbook();
  await src.xlsx.readFile(input!);

  // Timestamp suffix carried over from the input filename when it has one
  // (`ExtendedReach_Reports_2026-09-01_2359.xlsx` -> `20260901_2359`), so
  // repeated runs sort chronologically the same way the exporter's own
  // `_YYYYMMDD` suffix does.
  const base = path.basename(input!, path.extname(input!));
  const stampMatch = base.match(/(\d{4}-\d{2}-\d{2})_(\d{4})$/);
  const stamp = stampMatch ? `${stampMatch[1].replace(/-/g, "")}${stampMatch[2]}` : Date.now().toString();

  const written: string[] = [];
  const skipped: string[] = [];

  for (const sheet of src.worksheets) {
    const slug = sheet.name.trim();
    if (!KNOWN_SLUGS.has(slug)) {
      skipped.push(slug);
      continue;
    }

    const out = new ExcelJS.Workbook();
    const copy = out.addWorksheet(slug);
    sheet.eachRow({ includeEmpty: true }, (row, rowNumber) => {
      const values = Array.isArray(row.values) ? row.values.slice(1) : [];
      copy.getRow(rowNumber).values = values;
    });

    const filename = `${slug}_${stamp}.xlsx`;
    const outPath = path.join(outDir, filename);
    await out.xlsx.writeFile(outPath);
    written.push(filename);
  }

  console.log(`Wrote ${written.length} file(s) to ${outDir}:`);
  for (const f of written) console.log(`  ${f}`);
  if (skipped.length) {
    console.log(`\nSkipped ${skipped.length} sheet(s) with no matching report spec:`);
    for (const s of skipped) console.log(`  ${s}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
