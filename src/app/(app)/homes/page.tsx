import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { can } from "@/lib/rbac";
import { recordAccess } from "@/lib/audit";
import { getDataset } from "@/lib/zoho/client";
import { Card, KpiCard } from "@/components/ui";

export default async function HomesPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  // Route-level guard: staff don't get the homes register, same as compliance.
  if (!can(user, "viewHomesRegister")) {
    recordAccess({ id: user.id, role: user.role }, "denied", { meta: { route: "homes" } });
    redirect("/dashboard");
  }

  const data = await getDataset();
  const homes = data.homes ?? [];

  recordAccess({ id: user.id, role: user.role }, "view_homes", { meta: { homes: homes.length } });

  const withOpenBeds = homes.filter((h) => (h.bedsAvailable ?? 0) > 0);
  const totalOpenBeds = homes.reduce((sum, h) => sum + (h.bedsAvailable ?? 0), 0);

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Foster homes</h1>
        <p className="mt-1 text-[15px] text-ink-soft">
          Licensed home capacity from ExtendedReach&rsquo;s Available Homes export. Home
          addresses, phone numbers, and current placements are not shown here — this view is
          capacity only.
        </p>
      </header>

      {homes.length === 0 ? (
        <Card>
          <p className="text-[15px] text-ink-soft">
            No open-beds export found yet. This report (<code>openbeds</code>) has not been
            confirmed against a real ExtendedReach export in this environment.
          </p>
        </Card>
      ) : (
        <>
          <section className="mb-6 grid gap-4 sm:grid-cols-3">
            <KpiCard label="Homes tracked" value={String(homes.length)} />
            <KpiCard
              label="Homes with open beds"
              value={String(withOpenBeds.length)}
              tone={withOpenBeds.length ? "good" : "warn"}
            />
            <KpiCard label="Open beds, agency-wide" value={String(totalOpenBeds)} />
          </section>

          <Card className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-[14px]">
                <thead>
                  <tr className="text-[12px] uppercase tracking-wide text-muted">
                    <th className="px-5 py-3 font-semibold">Home</th>
                    <th className="px-5 py-3 font-semibold">License type</th>
                    <th className="px-5 py-3 font-semibold">Age range</th>
                    <th className="px-5 py-3 font-semibold">Gender</th>
                    <th className="px-5 py-3 font-semibold">Open beds</th>
                    <th className="px-5 py-3 font-semibold">Last placement</th>
                  </tr>
                </thead>
                <tbody>
                  {homes
                    .slice()
                    .sort((a, b) => (b.bedsAvailable ?? 0) - (a.bedsAvailable ?? 0))
                    .map((h) => (
                      <tr key={h.id} className="border-t border-line">
                        <td className="px-5 py-3 font-medium text-ink tnum">{h.displayId}</td>
                        <td className="px-5 py-3 text-ink-soft">{h.licenseType || "—"}</td>
                        <td className="px-5 py-3 text-ink-soft">{h.ageRange || "—"}</td>
                        <td className="px-5 py-3 text-ink-soft">{h.gender || "—"}</td>
                        <td className="px-5 py-3 text-ink-soft tnum">
                          {h.bedsAvailable ?? "—"}
                        </td>
                        <td className="px-5 py-3 text-ink-soft tnum">
                          {h.lastPlacement || "—"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
