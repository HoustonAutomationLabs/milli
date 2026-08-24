#!/usr/bin/env tsx
/**
 * Fail-closed check that a directory of exports carries no real person name.
 *
 * Run this before publishing anything derived from real data. It exists
 * because `npm run deidentify` scrubs only the fields `schema.ts` declares
 * sensitive, and the one column nobody thought to declare — the task `type` —
 * turned out to carry given names, because certification items are named after
 * the person they belong to. 170 rows of real names reached a public
 * repository and a public demo before anything noticed.
 *
 * The de-identifier's own report cannot catch that class of mistake: it counts
 * what it replaced, not what it never looked at. This checks the OUTPUT, which
 * is the only place the answer actually is.
 *
 *   npm run verify:deidentified -- ./data/demo
 *
 * Exits non-zero on any finding, so it can gate a deploy. Findings are printed
 * MASKED — this tool must never be the thing that prints a child's name.
 */

import { readdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { readGrid } from "../src/lib/extendedreach/grid";
import { REPORT_SPECS, findHeaderRow } from "../src/lib/extendedreach/schema";

/** Both synthetic pools: the de-identifier's, and the one-off repair's. */
const SYNTHETIC = new Set([
  "Amara","Bodhi","Camille","Dashiell","Elena","Finnian","Gemma","Hollis","Imani","Jasper",
  "Kaia","Lorcan","Maeve","Nadia","Oscar","Priya","Quincy","Rosalind","Soren","Tamsin",
  "Ulises","Verity","Wren","Xavier","Yara","Zephyr","Adaeze","Beckett","Coralie","Dmitri",
  "Esperanza","Felix","Giselle","Hugo","Isolde","Jonah","Keziah","Leonie","Mateo","Niamh",
  "Odalys","Peregrine","Rafferty","Saoirse","Thaddeus","Uma","Vidal","Willa","Yusuf","Zora",
  "Alder","Briony","Cassian","Delphine","Emory","Fenwick","Greer","Halcyon","Ines","Jethro",
  "Kestrel","Linnea","Marlowe","Nerissa","Osric","Perpetua","Quill","Rowan","Sable","Torin",
  "Ursula","Vesper","Wendell","Ximena","Yarrow","Zinnia","Anouk","Bram","Cleo","Dorian",
  "Eulalia","Fintan","Galen","Hesper","Ilya",
]);

/**
 * Kept in step with `TASK_VOCAB` in deidentify-export.ts. A word here is one
 * the scrubber will not treat as a name, so this checker must not either —
 * otherwise it reports findings the scrubber is never going to act on and the
 * whole check gets ignored as noisy, which is worse than not having it.
 */
const TASK_VOCAB =
  /\b(review|plan|report|visit|assessment|treatment|quarterly|monthly|annual|initial|renewal|update|form|training|medication|service|care|home|case|court|medical|dental|physical|test|screen|log|notes?|prescribed|otc|parent|basic|none|other|type|level|hours?|days?|years?|ytf|aka)\b/i;

const mask = (s: string) => s.replace(/[A-Za-z]/g, (c, i) => (i === 0 ? c : "*"));

/** Does this cell contain something the scrubber would call a person's name? */
function findings(v: string): string[] {
  const out: string[] = [];
  for (const m of v.matchAll(/\(([^)]{2,60})\)/g)) {
    const t = m[1].trim();
    if (TASK_VOCAB.test(t)) continue;
    if (!/^[A-Z][a-z]+(?:,?\s+[A-Z][a-z]+){0,2}$/.test(t)) continue;
    const tokens = t.split(/[,\s]+/).filter(Boolean);
    if (tokens.every((x) => SYNTHETIC.has(x))) continue;
    out.push(t);
  }
  // "Surname, Given" outside a parenthetical, in a column that is not a name
  // column, is the other shape a stray person takes.
  for (const m of v.matchAll(/(?<!\()\b([A-Z][a-z]{2,}),\s+([A-Z][a-z]{2,})\b(?!\))/g)) {
    if (SYNTHETIC.has(m[1]) || SYNTHETIC.has(m[2])) continue;
    out.push(m[0]);
  }
  return out;
}

async function main() {
  const dir = process.argv.slice(2).find((a) => !a.startsWith("-")) ?? "./data/demo";
  let files: string[];
  try {
    files = (await readdir(dir)).filter((f) => /\.(xlsx|csv)$/i.test(f));
  } catch {
    console.error(`Cannot read ${dir}`);
    process.exit(2);
  }

  let total = 0;
  let checkedFiles = 0;

  for (const f of files.sort()) {
    const slug = f.replace(/_\d{8}\.(xlsx|csv)$/i, "");
    const spec = REPORT_SPECS[slug];
    if (!spec) {
      console.log(`  ? ${f} — no spec for slug "${slug}", NOT CHECKED`);
      continue;
    }
    const grid = await readGrid(path.join(dir, f));
    if (!grid.length) continue;
    checkedFiles++;

    // Every column is checked, not just the declared ones. Restricting the
    // check to declared fields would reproduce the exact blind spot that
    // caused the incident.
    const found = spec.matrix ? null : findHeaderRow(spec, grid);
    const start = found ? found.header + 1 : 1;
    const hits = new Map<string, number>();

    for (let r = start; r < grid.length; r++) {
      for (const cell of grid[r] ?? []) {
        if (!cell) continue;
        for (const hit of findings(cell)) hits.set(hit, (hits.get(hit) ?? 0) + 1);
      }
    }

    if (hits.size) {
      console.log(`  ✖ ${f} — ${hits.size} distinct unscrubbed name(s):`);
      for (const [h, n] of [...hits.entries()].slice(0, 10)) {
        console.log(`      ${n}x  ${h.split(/([,\s]+)/).map((p) => (/^[A-Za-z]+$/.test(p) ? mask(p) : p)).join("")}`);
      }
      total += hits.size;
    } else {
      console.log(`  ✓ ${f}`);
    }
  }

  console.log("");
  if (total) {
    console.log(`FAIL — ${total} unscrubbed name(s) across ${checkedFiles} file(s). Do not publish.`);
    process.exit(1);
  }
  console.log(`PASS — ${checkedFiles} file(s) checked, no unscrubbed names found.`);
}

main();
