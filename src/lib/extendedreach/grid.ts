/**
 * Reading an ExtendedReach export into a grid of strings.
 *
 * Both the loader (`exports.ts`) and the reconciliation tool
 * (`scripts/inspect-export.ts`) need exactly the same view of a file, so the
 * reader lives here rather than being copied into each. A difference between
 * the two would mean `inspect:export` could pass on a file the loader then
 * fails to read, which is the one thing that tool exists to prevent.
 *
 * Formats
 * -------
 * The audit recorded "Excel only — no CSV anywhere", and that holds for the
 * report views in the Reports/Rosters/Tasks menus. It does not hold for
 * everything: the Compliance Tracking custom reports (`A_COMPLIANCE_*`) and
 * "Reports Completed by Date" have both arrived as `.csv`. Rather than force
 * a manual conversion step before every reconciliation — a step that has to
 * happen on a machine holding real PHI — the reader accepts both.
 *
 * Encoding
 * --------
 * The CSV exports are Windows-1252, not UTF-8: a real file contained a
 * cp1252 curly apostrophe in a column header ("Child's Service Plan"), which
 * decodes to U+FFFD under UTF-8 and would make that header text — the exact
 * thing reconciliation matches on — unmatchable. Decode as UTF-8 strictly and
 * fall back to Windows-1252 when that fails, which is unambiguous: any byte
 * sequence that is not valid UTF-8 is not a UTF-8 file.
 */

import { readFile } from "node:fs/promises";
import ExcelJS from "exceljs";

/** Rows of a sheet as trimmed strings, header row included. */
export type Grid = string[][];

/** Is this a file the reader understands? */
export function isReadableExport(file: string): boolean {
  return /\.(xlsx|csv)$/i.test(file);
}

/** Decode a buffer as UTF-8, falling back to Windows-1252. */
export function decodeText(buf: Buffer): string {
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(buf);
  } catch {
    return new TextDecoder("windows-1252").decode(buf);
  }
}

/** One Excel cell as a trimmed string, resolving formulas and rich text. */
function cellText(v: ExcelJS.CellValue): string {
  if (v == null) return "";
  if (v instanceof Date) return v.toISOString().slice(0, 10);
  if (typeof v === "object" && "text" in v) return String((v as { text?: unknown }).text ?? "").trim();
  if (typeof v === "object" && "result" in v) return String((v as { result?: unknown }).result ?? "").trim();
  return String(v).trim();
}

async function readXlsx(file: string): Promise<Grid> {
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(await readFile(file));
  const ws = wb.worksheets[0];
  if (!ws) return [];

  const grid: Grid = [];
  ws.eachRow({ includeEmpty: false }, (row) => {
    const cells: string[] = [];
    row.eachCell({ includeEmpty: true }, (cell, col) => {
      cells[col - 1] = cellText(cell.value);
    });
    grid.push(Array.from(cells, (c) => c ?? ""));
  });
  return grid;
}

/**
 * Parse CSV per RFC 4180: comma-separated, `"` quoting, `""` for a literal
 * quote inside a quoted field, and newlines permitted inside quotes. The
 * rejected-tasks export carries multi-line rejection reasons, so quoted
 * newlines are not hypothetical.
 */
export function parseCsv(text: string): Grid {
  const rows: Grid = [];
  let row: string[] = [];
  let cur = "";
  let quoted = false;
  let sawAny = false;

  const endField = () => {
    row.push(cur.trim());
    cur = "";
    sawAny = true;
  };
  const endRow = () => {
    endField();
    rows.push(row);
    row = [];
    sawAny = false;
  };

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') {
        cur += '"';
        i++;
      } else if (c === '"') {
        quoted = false;
      } else {
        cur += c;
      }
      continue;
    }
    if (c === '"') quoted = true;
    else if (c === ",") endField();
    else if (c === "\n") endRow();
    else if (c !== "\r") cur += c;
  }
  if (cur || sawAny || row.length) endRow();

  // A trailing newline yields one empty row; it is layout, not data.
  while (rows.length && rows[rows.length - 1].every((c) => !c)) rows.pop();
  return rows;
}

async function readCsv(file: string): Promise<Grid> {
  return parseCsv(decodeText(await readFile(file)));
}

/** Read the first worksheet of a workbook, or a CSV, into a grid. */
export async function readGrid(file: string): Promise<Grid> {
  return /\.csv$/i.test(file) ? readCsv(file) : readXlsx(file);
}
