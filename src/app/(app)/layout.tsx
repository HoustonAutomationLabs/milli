import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { PERMISSIONS, can } from "@/lib/rbac";
import { signOut } from "@/app/actions";
import { effectiveDataSourceMode } from "@/lib/zoho/client";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const activeMode = await effectiveDataSourceMode();

  const nav = [
    { href: "/morning", label: "Morning board", show: true },
    { href: "/dashboard", label: "Overview", show: true },
    { href: "/caseload", label: "Caseload", show: true },
    { href: "/compliance", label: "Compliance", show: can(user, "viewComplianceRegister") },
    { href: "/homes", label: "Homes", show: can(user, "viewHomesRegister") },
    { href: "/training", label: "Training", show: true },
    { href: "/admin/users", label: "Manage users", show: can(user, "manageUsers") },
  ].filter((n) => n.show);

  return (
    <div className="min-h-screen md:grid md:grid-cols-[248px_1fr]">
      <aside className="border-b border-line bg-surface md:border-b-0 md:border-r md:min-h-screen">
        <div className="flex items-center justify-between p-5 md:block">
          <div>
            <div className="text-[13px] font-semibold uppercase tracking-[0.14em] text-accent">
              Milli
            </div>
            <div className="mt-0.5 text-[13px] text-muted">Casework Dashboard</div>
          </div>
        </div>

        <nav className="px-3 pb-4 md:pb-0">
          <ul className="flex gap-1 md:flex-col">
            {nav.map((n) => (
              <li key={n.href}>
                <Link
                  href={n.href}
                  className="block rounded-lg px-3 py-2 text-[15px] font-medium text-ink-soft hover:bg-surface-2 hover:text-ink"
                >
                  {n.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="hidden md:block md:mt-auto md:p-5">
          <div className="rounded-xl border border-line bg-surface-2 p-3">
            <div className="text-[14px] font-medium text-ink">{user.name}</div>
            <div className="text-[12px] text-muted">{PERMISSIONS[user.role].label}</div>
            <form action={signOut} className="mt-3">
              <button
                type="submit"
                className="text-[13px] font-medium text-accent hover:underline underline-offset-2"
              >
                Sign out
              </button>
            </form>
          </div>
        </div>
      </aside>

      <div className="flex flex-col">
        {/*
          The banner states which data is on screen and that sign-in is not
          real. Both matter to anyone being shown this: a synthetic figure and
          a de-identified one carry very different weight, and neither should
          be mistaken for a live record. The old copy pointed at the Zoho
          Analytics feed, which the exec team declined and the system audit
          found unnecessary — see docs/extendedreach-audit.md.
        */}
        <div className="border-b border-line bg-warn-bg px-6 py-2 text-[13px] font-medium text-warn">
          {activeMode === "mock"
            ? "Demo — synthetic data, not real records. Sign-in is stubbed; anyone with this link can view."
            : "Demo — real figures on de-identified data: counts and dates are real, every name is synthetic. Sign-in is stubbed; anyone with this link can view."}
        </div>
        <main className="flex-1 px-6 py-8 md:px-10">{children}</main>
      </div>
    </div>
  );
}
