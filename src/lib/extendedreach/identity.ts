/**
 * Pseudonymisation for ExtendedReach exports.
 *
 * No ExtendedReach report exposes a stable Case ID or Worker ID — every view
 * identifies people by name only (docs/extendedreach-audit.md). Names are
 * therefore the join key across reports, which has two consequences:
 *
 *   1. Names must be normalised aggressively before joining, or the same child
 *      appears twice because one report wrote "Muse, Ski'inez" and another
 *      "MUSE, SKI'INEZ ".
 *   2. Every broad view needs a non-PHI identifier. We derive one from the
 *      normalised name so it is stable across runs without persisting a
 *      lookup table anywhere.
 *
 * The derived id is a truncated SHA-256 digest. It is a display pseudonym, not
 * a security boundary — the real protection is server-side scoping in
 * `src/lib/rbac.ts`. It exists so a caseload count, a chart, or an AI-written
 * briefing can reference a case without carrying the child's name.
 *
 * Ask the vendor to add a real Case ID column; it removes this whole module.
 */

import { createHash } from "node:crypto";

/**
 * Collapse the cosmetic variation between reports so the same person joins to
 * the same key: trim, collapse internal whitespace, drop the space after the
 * surname comma, and uppercase.
 *
 * Deliberately conservative — it does not strip punctuation or accents, since
 * "O'Brien" and "OBrien" may genuinely be different families.
 */
export function normaliseName(raw: string): string {
  return raw
    .replace(/\s+/g, " ")
    .replace(/\s*,\s*/g, ",")
    .trim()
    .toUpperCase();
}

/** Stable, non-reversible display id for a case, e.g. "FC-7A3E91". */
export function caseDisplayId(childName: string): string {
  const digest = createHash("sha256").update(normaliseName(childName)).digest("hex");
  return `FC-${digest.slice(0, 6).toUpperCase()}`;
}

/**
 * Stable, non-reversible display id for a foster home, e.g. "HM-4B12C9".
 *
 * Home obligations (licensing, insurance, fire-drill logs) live in the same
 * compliance list as case obligations but are a different subject entirely.
 * The distinct prefix keeps that visible rather than letting a home masquerade
 * as a case that simply failed to join.
 */
export function homeDisplayId(homeName: string): string {
  const digest = createHash("sha256").update(normaliseName(homeName)).digest("hex");
  return `HM-${digest.slice(0, 6).toUpperCase()}`;
}

/** Stable internal id for a worker, e.g. "wkr-2c81f0". */
export function workerId(name: string): string {
  const digest = createHash("sha256").update(normaliseName(name)).digest("hex");
  return `wkr-${digest.slice(0, 6)}`;
}

/**
 * Initials for compact display: "Muse, Kayla Rena" -> "M.K."
 * Falls back to the first two characters when the shape is unexpected.
 */
export function initials(name: string): string {
  const parts = normaliseName(name)
    .split(/[,\s]+/)
    .filter(Boolean);
  if (parts.length === 0) return "??";
  const picked = parts.slice(0, 2).map((p) => p[0]);
  return picked.join(".") + ".";
}
