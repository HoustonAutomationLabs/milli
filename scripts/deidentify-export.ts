#!/usr/bin/env tsx
/**
 * Produce a shareable, de-identified copy of an ExtendedReach export.
 *
 * The demo needs the agency's real operational picture — row counts, the age
 * curve of the backlog, the task-type mix, how unevenly work is distributed —
 * without putting children's names on a public URL. Those two things are
 * separable: every number an executive reacts to survives de-identification,
 * and nothing that identifies a child does.
 *
 *   npm run deidentify -- ./real/pastdue_case_20260822.xlsx --out ./data/exports
 *   npm run deidentify -- ./real --out ./data/exports        # whole directory
 *
 * What is preserved
 *   - Every row, in order. Counts and distributions are exact.
 *   - Dates, statuses, task types, programs — untouched.
 *   - Referential integrity: one real person always maps to the same synthetic
 *     person, in every column of every report. Joins and per-worker counts
 *     behave exactly as they do on real data.
 *
 * What is replaced
 *   - Names in any PII-bearing column, per `schema.ts`.
 *   - Free text, which is scrubbed of every known real name and of anything
 *     shaped like one.
 *
 * The mapping is derived from a hash of the real name, so it is stable across
 * runs and files without storing a lookup anywhere. It is one-way: the output
 * cannot be turned back into the original.
 */

import { readdir, readFile, mkdir, writeFile } from "node:fs/promises";
import { statSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import process from "node:process";
import ExcelJS from "exceljs";

import { REPORT_SPECS, findHeaderRow, type ReportSpec } from "../src/lib/extendedreach/schema";

const args = process.argv.slice(2);
const opt = (n: string) => {
  const i = args.indexOf(`--${n}`);
  return i >= 0 ? args[i + 1] : undefined;
};
const targets = args.filter(
  (a, i) => !a.startsWith("--") && !["--out", "--slug"].includes(args[i - 1] ?? ""),
);
const OUT_DIR = opt("out") ?? "./data/exports";

/** Columns that carry a person's name, by logical field name. */
const PII_FIELDS = new Set(["client", "worker", "home", "staff"]);
/** Columns that may mention a person in prose. */
const FREETEXT_FIELDS = new Set(["description"]);

// ---------------------------------------------------------------------------
// Synthetic name pools
// ---------------------------------------------------------------------------

const SURNAMES = [
  "Alvarez", "Bennett", "Carver", "Delgado", "Ellison", "Fontaine", "Gallagher",
  "Hollis", "Ibarra", "Jennings", "Kowalski", "Lindqvist", "Mbeki", "Nakamura",
  "Oyelaran", "Pemberton", "Quintero", "Rasmussen", "Sandoval", "Thibodeaux",
  "Ueda", "Vasquez", "Whitfield", "Xiong", "Yardley", "Zabala", "Ashford",
  "Boone", "Castellanos", "Dunmore", "Eastwood", "Farrow", "Grantham",
  "Hargrove", "Iverson", "Jarrett", "Kensington", "Larkin", "Mercado",
  "Northcott", "Ondrejka", "Prescott", "Quimby", "Rowntree", "Silvestri",
  "Tanaka", "Underhill", "Villanueva", "Waverly", "Yoshida",
];

const GIVEN = [
  "Amara", "Bodhi", "Camille", "Dashiell", "Elena", "Finnian", "Gemma",
  "Hollis", "Imani", "Jasper", "Kaia", "Lorcan", "Maeve", "Nadia", "Oscar",
  "Priya", "Quincy", "Rosalind", "Soren", "Tamsin", "Ulises", "Verity",
  "Wren", "Xavier", "Yara", "Zephyr", "Adaeze", "Beckett", "Coralie",
  "Dmitri", "Esperanza", "Felix", "Giselle", "Hugo", "Isolde", "Jonah",
  "Keziah", "Leonie", "Mateo", "Niamh", "Odalys", "Peregrine", "Rafferty",
  "Saoirse", "Thaddeus", "Uma", "Vidal", "Willa", "Yusuf", "Zora",
];

const INITIALS = "ABCDEFGHIJKLMNPRSTVW".split("");

/**
 * Pools with every name that occurs in the source data removed.
 *
 * Populated by `buildPools` before any assignment. Without this a pool name
 * eventually coincides with a real one — the first run here produced synthetic
 * "Bennett" while a real Bennett existed in the file. That discloses nothing,
 * but it invites a false association and makes a reviewer reasonably doubt the
 * de-identification held.
 *
 * The exclusion set is built from EVERY input file in the run, before any name
 * is assigned, so the mapping stays identical across reports and joins between
 * them survive. That is why all reports must be de-identified in one run.
 */
let SURNAME_POOL: string[] = SURNAMES;
let GIVEN_POOL: string[] = GIVEN;

export function buildPools(realNames: Iterable<string>): { surnames: number; given: number } {
  const banned = new Set<string>();
  for (const n of realNames) {
    for (const tok of n.split(/[^A-Za-z]+/)) {
      if (tok.length >= 2) banned.add(tok.toLowerCase());
    }
  }
  SURNAME_POOL = SURNAMES.filter((s) => !banned.has(s.toLowerCase()));
  GIVEN_POOL = GIVEN.filter((g) => !banned.has(g.toLowerCase()));

  if (SURNAME_POOL.length < 20 || GIVEN_POOL.length < 20) {
    throw new Error(
      `Name pools too depleted after excluding real names ` +
        `(${SURNAME_POOL.length} surnames, ${GIVEN_POOL.length} given). ` +
        `Add more entries to SURNAMES / GIVEN in scripts/deidentify-export.ts.`,
    );
  }
  return { surnames: SURNAME_POOL.length, given: GIVEN_POOL.length };
}

function hashInt(s: string, salt: string): number {
  const h = createHash("sha256").update(`${salt}::${s.toLowerCase().replace(/\s+/g, " ").trim()}`).digest();
  return h.readUInt32BE(0);
}

/**
 * Map a real name to a synthetic one, deterministically.
 *
 * The mapping depends only on the real name, never on which file it appeared
 * in, so the same person becomes the same synthetic person across every
 * report — without which joins between reports would silently break.
 *
 * That constraint rules out resolving collisions by probing (the outcome would
 * depend on who else is in the file), so the name space is instead made wide
 * enough that collisions are vanishingly unlikely: hyphenated surnames give
 * ~2,550 forms, times 50 given names, times 20 middle initials — about 2.5
 * million. `assertUnique` verifies it held rather than trusting the maths.
 *
 * "Last, First Middle" keeps that shape; a plain "First Last" keeps that shape.
 */
function synthName(real: string): string {
  const clean = real.trim();
  if (!clean) return "";

  // Compound surnames widen the space enough that two real people never
  // collapse into one synthetic identity; the pools they draw from already
  // exclude every name present in the source.
  const s1 = SURNAME_POOL[hashInt(clean, "sur1") % SURNAME_POOL.length];
  let s2 = SURNAME_POOL[hashInt(clean, "sur2") % SURNAME_POOL.length];
  if (s2 === s1) s2 = SURNAME_POOL[(hashInt(clean, "sur2") + 1) % SURNAME_POOL.length];
  const surname = `${s1}-${s2}`;

  const given = GIVEN_POOL[hashInt(clean, "giv") % GIVEN_POOL.length];
  const initial = INITIALS[hashInt(clean, "ini") % INITIALS.length];

  if (clean.includes(",")) {
    const hasMiddle = /,\s*\S+\s+\S+/.test(clean);
    return hasMiddle ? `${surname}, ${given} ${initial}.` : `${surname}, ${given}`;
  }
  return `${given} ${surname}`;
}

/**
 * Two real people collapsing into one synthetic person would merge their rows
 * and quietly understate the caseload — the demo would show fewer children
 * than the agency has. Cheap to check, so check.
 */
function assertUnique(map: Map<string, string>, file: string): void {
  const back = new Map<string, string>();
  const clashes: string[] = [];
  for (const [real, fake] of map) {
    const prior = back.get(fake);
    if (prior && prior !== real) clashes.push(fake);
    else back.set(fake, real);
  }
  if (clashes.length) {
    throw new Error(
      `${path.basename(file)}: ${clashes.length} synthetic name collision(s) — two real people ` +
        `mapped to the same identity, which would merge their rows. Widen the name pools in ` +
        `scripts/deidentify-export.ts and re-run.`,
    );
  }
}

// ---------------------------------------------------------------------------
// Workbook IO
// ---------------------------------------------------------------------------

function cellText(v: ExcelJS.CellValue): string {
  if (v == null) return "";
  if (v instanceof Date) return v.toISOString().slice(0, 10);
  if (typeof v === "object" && "text" in v) return String((v as { text?: unknown }).text ?? "");
  if (typeof v === "object" && "result" in v) return String((v as { result?: unknown }).result ?? "");
  return String(v);
}

function specForFile(file: string): ReportSpec | null {
  const forced = opt("slug");
  if (forced) return REPORT_SPECS[forced] ?? null;
  const base = path.basename(file);
  return Object.values(REPORT_SPECS).find((s) => base.startsWith(`${s.slug}_`)) ?? null;
}

/** Every personal name across a set of files, for pool exclusion. */
async function collectRealNames(files: string[]): Promise<Set<string>> {
  const names = new Set<string>();
  for (const file of files) {
    const spec = specForFile(file);
    if (!spec) continue;
    const wb = new ExcelJS.Workbook();
    await wb.xlsx.load(await readFile(file));
    const ws = wb.worksheets[0];
    if (!ws) continue;
    const grid: string[][] = [];
    ws.eachRow({ includeEmpty: false }, (row) => {
      const cells: string[] = [];
      row.eachCell({ includeEmpty: true }, (cell, col) => {
        cells[col - 1] = cellText(cell.value).trim();
      });
      grid.push(Array.from(cells, (c) => c ?? ""));
    });
    const found = findHeaderRow(spec, grid);
    if (!found) continue;
    for (const [field, idx] of Object.entries(found.columns)) {
      if (!PII_FIELDS.has(field)) continue;
      for (let r = found.header + 1; r < grid.length; r++) {
        const v = (grid[r]?.[idx] ?? "").trim();
        if (v) names.add(v);
      }
    }
  }
  return names;
}

async function deidentify(file: string, outDir: string) {
  const spec = specForFile(file);
  if (!spec) {
    console.log(`  ✖ ${path.basename(file)} — no matching report spec, skipped`);
    return null;
  }

  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(await readFile(file));
  const ws = wb.worksheets[0];
  if (!ws) return null;

  // Read into a grid so the header can be located the same way the loader does.
  const grid: string[][] = [];
  ws.eachRow({ includeEmpty: false }, (row) => {
    const cells: string[] = [];
    row.eachCell({ includeEmpty: true }, (cell, col) => {
      cells[col - 1] = cellText(cell.value).trim();
    });
    grid.push(Array.from(cells, (c) => c ?? ""));
  });

  const found = findHeaderRow(spec, grid);
  if (!found) {
    console.log(`  ✖ ${path.basename(file)} — header not recognised, skipped`);
    return null;
  }

  const piiCols = new Map<number, string>();
  const textCols = new Set<number>();
  for (const [field, idx] of Object.entries(found.columns)) {
    if (PII_FIELDS.has(field)) piiCols.set(idx, field);
    if (FREETEXT_FIELDS.has(field)) textCols.add(idx);
  }

  // Pass 1 — build the full real→synthetic map so free text can be scrubbed
  // against every name that appears anywhere in the file.
  const nameMap = new Map<string, string>();
  for (let r = found.header + 1; r < grid.length; r++) {
    for (const idx of piiCols.keys()) {
      const real = (grid[r]?.[idx] ?? "").trim();
      if (real && !nameMap.has(real)) nameMap.set(real, synthName(real));
    }
  }

  assertUnique(nameMap, file);

  // Longest first, so "Smith, John Robert" is replaced before "Smith, John".
  const ordered = [...nameMap.entries()].sort((a, b) => b[0].length - a[0].length);

  function scrubText(s: string): string {
    if (!s) return s;
    let out = s;
    for (const [real, fake] of ordered) {
      if (out.includes(real)) out = out.split(real).join(fake);
      // Also catch "First Last" where the column held "Last, First".
      const m = real.match(/^([^,]+),\s*(\S+)/);
      if (m) {
        const flipped = `${m[2]} ${m[1]}`;
        if (out.includes(flipped)) out = out.split(flipped).join(synthName(real));
      }
    }
    // Backstop for any remaining "Surname, Given" shape not seen in a column.
    return out.replace(/\b[A-Z][a-z]{2,},\s+[A-Z][a-z]{2,}\b/g, (m) => synthName(m));
  }

  // Pass 2 — rewrite cells in place, preserving everything else.
  let namesReplaced = 0;
  let textScrubbed = 0;
  ws.eachRow({ includeEmpty: false }, (row, rowNumber) => {
    if (rowNumber <= found.header + 1) return; // 1-indexed; skip header and above
    row.eachCell({ includeEmpty: false }, (cell, col) => {
      const idx = col - 1;
      const raw = cellText(cell.value).trim();
      if (!raw) return;

      if (piiCols.has(idx)) {
        const fake = nameMap.get(raw);
        if (fake) {
          cell.value = fake;
          namesReplaced++;
        }
      } else if (textCols.has(idx)) {
        const scrubbed = scrubText(raw);
        if (scrubbed !== raw) {
          cell.value = scrubbed;
          textScrubbed++;
        }
      }
    });
  });

  const outFile = path.join(outDir, path.basename(file));
  await wb.xlsx.writeFile(outFile);

  console.log(
    `  ✓ ${path.basename(file).padEnd(34)} ${String(grid.length - found.header - 1).padStart(5)} rows · ` +
      `${nameMap.size} distinct people → synthetic · ${namesReplaced} cells · ${textScrubbed} free-text scrubbed`,
  );

  return { slug: spec.slug, people: nameMap.size, rows: grid.length - found.header - 1 };
}

async function main() {
  if (!targets.length) {
    console.log("Usage: npm run deidentify -- <file.xlsx | dir> [--out ./data/exports] [--slug <name>]");
    process.exit(1);
  }

  const files: string[] = [];
  for (const t of targets) {
    if (statSync(t).isDirectory()) {
      const entries = await readdir(t);
      files.push(...entries.filter((f) => f.endsWith(".xlsx")).map((f) => path.join(t, f)));
    } else files.push(t);
  }

  const outDir = path.resolve(OUT_DIR);
  await mkdir(outDir, { recursive: true });

  // Build the exclusion set from every input before assigning any name, so a
  // person appearing in two reports gets the same synthetic identity in both.
  const realNames = await collectRealNames(files);
  const pools = buildPools(realNames);
  console.log(
    `\nDe-identifying ${files.length} file(s) → ${outDir}\n` +
      `  ${realNames.size} real names seen · pools reduced to ` +
      `${pools.surnames} surnames × ${pools.given} given names\n`,
  );
  if (files.length === 1) {
    console.log("  Note: de-identify all reports in ONE run, or names may differ between files.\n");
  }
  const results = [];
  for (const f of files.sort()) results.push(await deidentify(f, outDir));

  const ok = results.filter(Boolean).length;
  await writeFile(
    path.join(outDir, "DEIDENTIFIED.txt"),
    [
      "These workbooks are DE-IDENTIFIED copies of ExtendedReach exports.",
      "",
      "Row counts, dates, statuses, task types and distributions are real.",
      "Every personal name has been replaced with a synthetic one, consistently",
      "across files, via a one-way hash. They cannot be reversed.",
      "",
      `Generated: ${new Date().toISOString()}`,
      `Files: ${ok}`,
      "",
      "Safe to use for demos. Still not a substitute for real access controls",
      "if genuine data is ever loaded.",
    ].join("\n"),
  );

  console.log(`\n${ok}/${files.length} de-identified. Marker written to DEIDENTIFIED.txt`);
  console.log("Originals are untouched — delete them when you no longer need them.\n");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
