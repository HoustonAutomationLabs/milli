"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export interface PeriodOption {
  value: string;
  label: string;
}

/**
 * Year -> month -> week cascade, driving the page via URL search params
 * (?year=&month=&week=) so a filtered view is a link someone can share, and
 * the server component re-renders with real data rather than a client-only
 * illusion of filtering.
 */
export function PeriodFilter({
  years,
  months,
  weeks,
}: {
  years: PeriodOption[];
  months: PeriodOption[];
  weeks?: PeriodOption[];
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const year = searchParams.get("year") ?? "";
  const month = searchParams.get("month") ?? "";
  const week = searchParams.get("week") ?? "";

  function navigate(next: { year?: string; month?: string; week?: string }) {
    const params = new URLSearchParams();
    if (next.year) params.set("year", next.year);
    if (next.month) params.set("month", next.month);
    if (next.week) params.set("week", next.week);
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  const selectClass =
    "rounded-lg border border-line bg-surface px-3 py-1.5 text-[14px] text-ink";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        aria-label="Year"
        value={year}
        onChange={(e) => navigate({ year: e.target.value || undefined })}
        className={selectClass}
      >
        <option value="">All years</option>
        {years.map((y) => (
          <option key={y.value} value={y.value}>
            {y.label}
          </option>
        ))}
      </select>

      {year ? (
        <select
          aria-label="Month"
          value={month}
          onChange={(e) => navigate({ year, month: e.target.value || undefined })}
          className={selectClass}
        >
          <option value="">All months</option>
          {months.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      ) : null}

      {year && month && weeks && weeks.length > 0 ? (
        <select
          aria-label="Week"
          value={week}
          onChange={(e) => navigate({ year, month, week: e.target.value || undefined })}
          className={selectClass}
        >
          <option value="">All weeks</option>
          {weeks.map((w) => (
            <option key={w.value} value={w.value}>
              {w.label}
            </option>
          ))}
        </select>
      ) : null}
    </div>
  );
}
