import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { can } from "@/lib/rbac";
import { recordAccess } from "@/lib/audit";
import { boundWorkerNames, resolveScope } from "@/lib/demo-roles";
import { getDataset } from "@/lib/zoho/client";
import { scopeDataset, upcomingItems } from "@/lib/metrics";
import {
  distinctYears,
  filterComplianceByPeriod,
  monthLabel,
  monthsInYearFromDates,
  weekLabel,
  weeksInMonthFromDates,
} from "@/lib/period";
import { Card, ComplianceBadge, KpiCard } from "@/components/ui";
import { PeriodFilter } from "@/components/period-filter";

export default async function CompliancePage({
  searchParams,
}: {
  searchParams: Promise<{ year?: string; month?: string; week?: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  // Route-level guard: staff don't get the compliance register.
  if (!can(user, "viewComplianceRegister")) {
    recordAccess({ id: user.id, role: user.role }, "denied", { meta: { route: "compliance" } });
    redirect("/dashboard");
  }

  const sp = await searchParams;
  const data = await getDataset();
  const { scope, boundTo } = resolveScope(user, data);
  const scoped = scopeDataset(data, scope);

  const periodActive = Boolean(sp.year);
  // Default view: outstanding obligations only, exactly as before. Once a
  // period is picked, switch to every dated obligation due in that window
  // regardless of its current state — the point of looking at a past month
  // is what was due then, not just what's still overdue today.
  const items = periodActive
    ? filterComplianceByPeriod(scoped.compliance, { year: sp.year, month: sp.month, week: sp.week })
    : upcomingItems(scoped, 100);
  const caseById = new Map(scoped.cases.map((c) => [c.id, c]));

  recordAccess({ id: user.id, role: user.role }, "view_compliance", {
    meta: { items: items.length },
  });

  const overdue = items.filter((i) => i.state === "overdue").length;
  const dueSoon = items.filter((i) => i.state === "due_soon").length;

  const dueDates = scoped.compliance.filter((i) => i.dueDate && !i.calendarOnly).map((i) => i.dueDate);
  const years = distinctYears(dueDates);
  const monthOptions = sp.year
    ? monthsInYearFromDates(dueDates, sp.year).map((m) => ({ value: m, label: monthLabel(m) }))
    : [];
  const weekOptions = sp.month
    ? weeksInMonthFromDates(dueDates, sp.month).map((w) => ({ value: w, label: weekLabel(w) }))
    : [];

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Compliance register</h1>
        <p className="mt-1 text-[15px] text-ink-soft">
          Date-driven obligations across your access — home visits, medical exams, court reports.
        </p>
      </header>

      <div className="mb-4">
        <PeriodFilter
          years={years.map((y) => ({ value: y, label: y }))}
          months={monthOptions}
          weeks={weekOptions}
        />
      </div>

      <p className="mb-6 text-[13px] text-muted">
        {periodActive
          ? "Showing every obligation due in this period, with its status as of today — a past period is not re-run as of that date, since the export only ever holds the current state."
          : "Showing outstanding obligations only. Pick a year above to browse everything due in a period, regardless of status."}
      </p>

      <section className="mb-6 grid gap-4 sm:grid-cols-3">
        <KpiCard label="Overdue" value={String(overdue)} tone={overdue ? "risk" : "good"} />
        <KpiCard label="Due within 7 days" value={String(dueSoon)} tone={dueSoon ? "warn" : "good"} />
        <KpiCard label="Cases tracked" value={String(scoped.cases.length)} />
      </section>

      <Card className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-[14px]">
            <thead>
              <tr className="text-[12px] uppercase tracking-wide text-muted">
                <th className="px-5 py-3 font-semibold">Obligation</th>
                <th className="px-5 py-3 font-semibold">Case</th>
                <th className="px-5 py-3 font-semibold">Due</th>
                <th className="px-5 py-3 font-semibold">State</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-t border-line">
                  <td className="px-5 py-3 font-medium text-ink">{item.label}</td>
                  <td className="px-5 py-3 text-ink-soft tnum">
                    {caseById.get(item.caseId)?.displayId ?? item.caseId}
                  </td>
                  <td className="px-5 py-3 text-ink-soft tnum">{item.dueDate}</td>
                  <td className="px-5 py-3">
                    <ComplianceBadge state={item.state} />
                  </td>
                </tr>
              ))}
              {items.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-muted">
                    Nothing outstanding.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
