import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { can } from "@/lib/rbac";
import { recordAccess } from "@/lib/audit";
import { boundWorkerNames, resolveScope } from "@/lib/demo-roles";
import { getDataset } from "@/lib/zoho/client";
import {
  agencyTrend,
  caseloadByWorker,
  computeKpis,
  scopeDataset,
  upcomingItems,
} from "@/lib/metrics";
import {
  distinctYears,
  filterByYear,
  monthLabel,
  monthsInYear,
  onTimeForMonth,
  trendForMonth,
} from "@/lib/period";
import { Card, ComplianceBadge, KpiCard, SectionTitle } from "@/components/ui";
import { TrendChart } from "@/components/trend-chart";
import { PeriodFilter } from "@/components/period-filter";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ year?: string; month?: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const sp = await searchParams;
  const data = await getDataset();
  const { scope, boundTo } = resolveScope(user, data);
  const scoped = scopeDataset(data, scope);
  const kpis = computeKpis(scoped);
  recordAccess({ id: user.id, role: user.role }, "view_dashboard", {
    meta: { cases: scoped.cases.length },
  });

  const upcoming = upcomingItems(scoped, 8);
  const trend = agencyTrend(data);
  const caseById = new Map(scoped.cases.map((c) => [c.id, c]));

  // Year -> month drill for the trend/on-time series only — the two things in
  // this dataset that are genuinely historical (see src/lib/period.ts). The
  // KPI tiles above stay as-of-today regardless of this filter; they're a
  // snapshot with no history to select from.
  const trendYears = distinctYears(trend.map((t) => t.month));
  const filteredTrend = filterByYear(trend, sp.year);
  const monthOptions = sp.year
    ? monthsInYear(trend, sp.year).map((m) => ({ value: m, label: monthLabel(m) }))
    : [];
  const monthDetail = sp.year && sp.month ? trendForMonth(filteredTrend, sp.month) : undefined;
  const onTimeMonth =
    sp.year && sp.month ? onTimeForMonth(data.onTime ?? [], sp.month) : undefined;

  const heading =
    user.role === "ceo"
      ? "Agency overview"
      : user.role === "manager"
        ? "Team overview"
        : "My caseload";

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{heading}</h1>
        <p className="mt-1 text-[15px] text-ink-soft">
          Signed in as {user.name}. You&rsquo;re seeing {scoped.cases.length} case
          {scoped.cases.length === 1 ? "" : "s"} within your access.
        </p>
      </header>

      <p className="mb-4 text-[13px] text-muted">
        The tiles below are as of today — the export doesn&rsquo;t keep a history of case
        counts to look back on.{" "}
        {can(user, "viewAgencyKpis") ? "The trend below does, and can be filtered by year and month." : null}
      </p>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Active cases" value={String(kpis.activeCases)} />
        <KpiCard
          label="Open intakes"
          value={String(kpis.intakes)}
          hint="Awaiting assignment"
        />
        <KpiCard
          label="Overdue items"
          value={String(kpis.overdueItems)}
          tone={kpis.overdueItems > 0 ? "risk" : "good"}
          hint="Visits, exams, reports"
        />
        <KpiCard
          label="Compliance rate"
          value={`${Math.round(kpis.complianceRate * 100)}%`}
          tone={kpis.complianceRate >= 0.9 ? "good" : "warn"}
          hint={kpis.avgCaseload ? `Avg ${kpis.avgCaseload.toFixed(1)} cases / worker` : "Cases not overdue"}
        />
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Trend — agency-level, CEO only (non-PHI aggregate). */}
        {can(user, "viewAgencyKpis") ? (
          <Card className="lg:col-span-2">
            {/*
              The period is derived, not asserted. This said "12 months" while
              the export carried 8, and the caseload cross-tab only holds the
              months the agency has recorded — so a hard-coded span is wrong
              the moment the data is anything other than a full year.
            */}
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
              <SectionTitle>
                Active cases &middot;{" "}
                {sp.year
                  ? `${filteredTrend.length} month${filteredTrend.length === 1 ? "" : "s"} in ${sp.year}`
                  : `${trend.length} month${trend.length === 1 ? "" : "s"}`}
              </SectionTitle>
              <span className="text-[13px] text-muted tnum">
                {trend.at(-1)?.activeCases} in {trend.at(-1)?.month}
              </span>
            </div>

            <div className="mb-4">
              <PeriodFilter
                years={trendYears.map((y) => ({ value: y, label: y }))}
                months={monthOptions}
              />
            </div>

            {monthDetail ? (
              <>
                <div className="grid gap-3 sm:grid-cols-3">
                  <KpiCard label={monthLabel(monthDetail.month)} value={String(monthDetail.activeCases)} hint="Active cases" />
                  <KpiCard label="Intakes that month" value={String(monthDetail.intakes)} />
                  <KpiCard label="Discharges that month" value={String(monthDetail.discharges)} />
                </div>
                {onTimeMonth ? (
                  <p className="mt-3 text-[13px] leading-snug text-muted">
                    On-time completion in {monthLabel(onTimeMonth.month)}:{" "}
                    <span className="tnum text-ink-soft">{onTimeMonth.onTimePct}%</span> across{" "}
                    <span className="tnum">{onTimeMonth.sample}</span> completed items.
                  </p>
                ) : (
                  <p className="mt-3 text-[13px] leading-snug text-muted">
                    No on-time completion data loaded for this month.
                  </p>
                )}
              </>
            ) : (
              <>
                <TrendChart data={filteredTrend} />
                {/*
                  The newest point is whatever the export captured, and exports
                  are taken mid-month. Without this the final month reads as a
                  sudden drop in caseload rather than an incomplete count — the
                  kind of thing an executive acts on.
                */}
                <p className="mt-3 text-[13px] leading-snug text-muted">
                  {filteredTrend[0]?.month ?? "—"} to {filteredTrend.at(-1)?.month ?? "—"}. The
                  latest month is counted up to the export date and may be incomplete, so a dip
                  at the right-hand end is not necessarily a fall in caseload.
                </p>
              </>
            )}
          </Card>
        ) : (
          <Card className="lg:col-span-2">
            <SectionTitle>Caseload by worker</SectionTitle>
            <ul className="mt-4 flex flex-col divide-y divide-line">
              {caseloadByWorker(data, scoped).map((w) => (
                <li key={w.caseworkerId} className="flex items-center justify-between py-2.5">
                  <span className="text-[15px] text-ink">{w.name}</span>
                  <span className="text-[14px] text-ink-soft tnum">
                    {w.total} cases
                    {w.overdue > 0 ? (
                      <span className="ml-2 text-risk">· {w.overdue} overdue</span>
                    ) : null}
                  </span>
                </li>
              ))}
              {scoped.cases.length === 0 ? (
                <li className="py-2.5 text-[14px] text-muted">No cases in scope.</li>
              ) : null}
            </ul>
          </Card>
        )}

        {/* Upcoming / overdue items — everyone, scoped. */}
        <Card>
          <SectionTitle>Needs attention</SectionTitle>
          <ul className="mt-4 flex flex-col gap-3">
            {upcoming.map((item) => {
              const c = caseById.get(item.caseId);
              return (
                <li key={item.id} className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-[14px] font-medium text-ink">{item.label}</div>
                    <div className="text-[13px] text-muted tnum">
                      {c?.displayId ?? item.caseId} · due {item.dueDate}
                    </div>
                  </div>
                  <ComplianceBadge state={item.state} />
                </li>
              );
            })}
            {upcoming.length === 0 ? (
              <li className="text-[14px] text-muted">Nothing due soon. Nice.</li>
            ) : null}
          </ul>
        </Card>
      </div>

      {/* CEO also sees the per-worker breakdown below the trend. */}
      {can(user, "viewAllTeams") ? (
        <Card className="mt-6">
          <SectionTitle>Caseload by worker</SectionTitle>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[420px] text-left text-[14px]">
              <thead>
                <tr className="text-[12px] uppercase tracking-wide text-muted">
                  <th className="py-2 pr-4 font-semibold">Worker</th>
                  <th className="py-2 pr-4 font-semibold">Team</th>
                  <th className="py-2 pr-4 font-semibold text-right">Cases</th>
                  <th className="py-2 font-semibold text-right">Overdue</th>
                </tr>
              </thead>
              <tbody>
                {caseloadByWorker(data, scoped).map((w) => (
                  <tr key={w.caseworkerId} className="border-t border-line">
                    <td className="py-2.5 pr-4 text-ink">{w.name}</td>
                    <td className="py-2.5 pr-4 text-ink-soft">{w.teamName}</td>
                    <td className="py-2.5 pr-4 text-right text-ink tnum">{w.total}</td>
                    <td className="py-2.5 text-right tnum" style={{ color: w.overdue ? "var(--risk)" : "var(--muted)" }}>
                      {w.overdue}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
