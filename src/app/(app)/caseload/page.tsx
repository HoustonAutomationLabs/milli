import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { scopeForUser } from "@/lib/rbac";
import { recordAccess } from "@/lib/audit";
import { getDataset } from "@/lib/zoho/client";
import { scopeDataset } from "@/lib/metrics";
import { Card, ComplianceBadge } from "@/components/ui";
import type { CaseStatus } from "@/lib/zoho/types";

const STATUS_LABEL: Record<CaseStatus, string> = {
  active: "Active",
  intake: "Intake",
  on_hold: "On hold",
  discharged: "Discharged",
};

const PLACEMENT_LABEL: Record<string, string> = {
  foster_home: "Foster home",
  kinship: "Kinship",
  residential: "Residential",
  unassigned: "Unassigned",
};

export default async function CaseloadPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const data = await getDataset();
  const scope = scopeForUser(user);
  const scoped = scopeDataset(data, scope);
  const workerName = new Map(data.caseworkers.map((w) => [w.id, w.name]));

  recordAccess({ id: user.id, role: user.role }, "view_caseload", {
    resourceIds: scoped.cases.map((c) => c.id),
    meta: { count: scoped.cases.length },
  });

  const rows = [...scoped.cases].sort((a, b) => {
    const order = { overdue: 0, due_soon: 1, ok: 2 } as const;
    return order[a.compliance] - order[b.compliance];
  });

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Caseload</h1>
        <p className="mt-1 text-[15px] text-ink-soft">
          {rows.length} case{rows.length === 1 ? "" : "s"} within your access, most urgent first.
        </p>
      </header>

      <Card className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-[14px]">
            <thead>
              <tr className="text-[12px] uppercase tracking-wide text-muted">
                <th className="px-5 py-3 font-semibold">Case</th>
                <th className="px-5 py-3 font-semibold">Child</th>
                <th className="px-5 py-3 font-semibold">Status</th>
                <th className="px-5 py-3 font-semibold">Placement</th>
                <th className="px-5 py-3 font-semibold">Worker</th>
                <th className="px-5 py-3 font-semibold">Compliance</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className="border-t border-line">
                  <td className="px-5 py-3 font-medium text-ink tnum">{c.displayId}</td>
                  {/* PHI: shown here because the scoped caseload is the point of
                      the view. Broad/aggregate views elsewhere use displayId. */}
                  <td className="px-5 py-3 text-ink-soft">{c.childName}</td>
                  <td className="px-5 py-3 text-ink-soft">{STATUS_LABEL[c.status]}</td>
                  <td className="px-5 py-3 text-ink-soft">
                    {PLACEMENT_LABEL[c.placementType] ?? c.placementType}
                  </td>
                  <td className="px-5 py-3 text-ink-soft">
                    {workerName.get(c.caseworkerId) ?? c.caseworkerId}
                  </td>
                  <td className="px-5 py-3">
                    <ComplianceBadge state={c.compliance} />
                  </td>
                </tr>
              ))}
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-muted">
                    No cases in scope.
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
