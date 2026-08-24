/**
 * Date arithmetic and the age cutoffs the dashboard reasons about.
 *
 * These live apart from the export loader because the morning triage board
 * needs the same thresholds and must not pull the workbook reader in to get
 * them. One definition, two consumers — a cutoff that drifts between the
 * loader and the UI would silently move items between tiers.
 */

/** Whole days between a due date and today; negative means still upcoming. */
export function daysOverdue(dueIso: string, today = new Date()): number {
  const due = new Date(`${dueIso}T00:00:00Z`);
  const now = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  return Math.round((now.getTime() - due.getTime()) / 86_400_000);
}

/** Whole days since a past date. Negative would mean the future. */
export function daysSince(iso: string, today = new Date()): number {
  return daysOverdue(iso, today);
}

/**
 * Age threshold, in days, beyond which an overdue item is treated as an
 * abandoned record rather than live work.
 *
 * The audit measured this against a real export: of 997 past-due case tasks,
 * 311 (31%) were over a year old, 115 over two years, the oldest 6.4 years.
 * Leadership had estimated ~50% — the real figure is lower, which makes the
 * live backlog *larger* than assumed, not smaller.
 *
 * Reporting one undifferentiated past-due count to an executive is misleading
 * in both directions, so nothing is dropped: every item is loaded, and this
 * cutoff decides which tier it is triaged into. Confirm the figure with the
 * exec team before it drives a write-off decision.
 */
export const ABANDONED_AFTER_DAYS = Number(process.env.ER_ABANDONED_AFTER_DAYS ?? 365);

/**
 * How far ahead "due soon" looks. Matches the horizon of ExtendedReach's own
 * "Due in Next 30 Days" grouping, so the dashboard's due-soon count is
 * reconcilable against the source report rather than being a second opinion.
 */
export const DUE_SOON_DAYS = 30;
