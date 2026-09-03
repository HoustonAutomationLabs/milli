/**
 * Year / month / week filtering for dashboard views.
 *
 * Two kinds of data behave very differently under a date filter, and mixing
 * them up would produce a dashboard that looks filtered but isn't telling the
 * truth:
 *
 *   - Genuinely historical series — `TrendPoint`/`OnTimePoint`, sourced from
 *     the `caseload` cross-tab and monthly on-time rollups, and per-item
 *     `dueDate`s on obligations. These can be sliced by real year/month/week
 *     because each point already carries the period it happened in.
 *   - Point-in-time snapshots — the open-cases roster, home capacity. These
 *     have no history: every pull overwrites the last one, so "51 open cases"
 *     is a fact about today, not about any month a filter might select. This
 *     module makes no attempt to fake a past value for those; the UI must say
 *     so instead of pretending a filter changed them.
 */

import type { ComplianceItem, OnTimePoint, TrendPoint } from "./zoho/types";

export function yearOf(monthOrDate: string): string {
  return monthOrDate.slice(0, 4);
}

/** Distinct years present in a list of "YYYY-MM" or "YYYY-MM-DD" keys, newest first. */
export function distinctYears(keys: string[]): string[] {
  return [...new Set(keys.filter(Boolean).map(yearOf))].sort((a, b) => b.localeCompare(a));
}

export function monthLabel(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** The Monday (ISO date) of the week containing this date — used as a stable, sortable week key. */
export function weekStart(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00Z");
  const isoDay = d.getUTCDay() || 7; // Mon=1 .. Sun=7
  d.setUTCDate(d.getUTCDate() - isoDay + 1);
  return d.toISOString().slice(0, 10);
}

export function weekLabel(weekStartDate: string): string {
  const start = new Date(weekStartDate + "T00:00:00Z");
  const end = new Date(start);
  end.setUTCDate(end.getUTCDate() + 6);
  const fmt = (d: Date) =>
    d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
  return `Week of ${fmt(start)}–${fmt(end)}`;
}

export function filterByYear<T extends { month: string }>(rows: T[], year?: string): T[] {
  if (!year) return rows;
  return rows.filter((r) => yearOf(r.month) === year);
}

/** Months present within a given year, sorted, from a monthly series. */
export function monthsInYear<T extends { month: string }>(rows: T[], year: string): string[] {
  return [...new Set(rows.filter((r) => yearOf(r.month) === year).map((r) => r.month))].sort();
}

export interface Period {
  year?: string;
  /** "YYYY-MM" */
  month?: string;
  /** "YYYY-MM-DD", the Monday of the week */
  week?: string;
}

/**
 * Every dated, non-calendar obligation whose due date falls in the given
 * period. Deliberately does NOT filter by current `state` — a past period is
 * "what was due then," and its current status (done, still open, written
 * off) is exactly what's worth showing, not something to hide.
 */
export function filterComplianceByPeriod(
  items: ComplianceItem[],
  period: Period,
): ComplianceItem[] {
  const dated = items.filter((i) => i.dueDate && !i.calendarOnly);
  if (period.week) return dated.filter((i) => weekStart(i.dueDate) === period.week);
  if (period.month) return dated.filter((i) => i.dueDate.slice(0, 7) === period.month);
  if (period.year) return dated.filter((i) => yearOf(i.dueDate) === period.year);
  return dated;
}

export function monthsInYearFromDates(dates: string[], year: string): string[] {
  return [...new Set(dates.filter((d) => yearOf(d) === year).map((d) => d.slice(0, 7)))].sort();
}

export function weeksInMonthFromDates(dates: string[], month: string): string[] {
  return [...new Set(dates.filter((d) => d.slice(0, 7) === month).map(weekStart))].sort();
}

export function onTimeForMonth(series: OnTimePoint[], month: string): OnTimePoint | undefined {
  return series.find((p) => p.month === month);
}

export function trendForMonth(series: TrendPoint[], month: string): TrendPoint | undefined {
  return series.find((p) => p.month === month);
}
