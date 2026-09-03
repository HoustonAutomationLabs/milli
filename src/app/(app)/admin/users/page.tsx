import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { can, PERMISSIONS, ROLES } from "@/lib/rbac";
import { recordAccess } from "@/lib/audit";
import { getDataset } from "@/lib/zoho/client";
import { loadRoster } from "@/lib/roster";
import { Card } from "@/components/ui";
import { deleteUser, upsertUser } from "./actions";

export default async function ManageUsersPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  if (!can(user, "manageUsers")) {
    recordAccess({ id: user.id, role: user.role }, "denied", { meta: { route: "admin/users" } });
    redirect("/dashboard");
  }

  const [data, roster] = await Promise.all([getDataset(), loadRoster()]);
  recordAccess({ id: user.id, role: user.role }, "view_admin_users", { meta: { entries: roster.length } });

  const teamName = new Map(data.teams.map((t) => [t.id, t.name]));

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Manage users</h1>
        <p className="mt-1 text-[15px] text-ink-soft">
          This list is the only thing that grants a dashboard login. Having a company Google
          account does not, on its own, let anyone sign in — an email has to be added here first,
          with the role and team it should see. Removing someone here removes their access.
        </p>
      </header>

      <Card className="mb-8">
        <h2 className="mb-4 text-[15px] font-semibold text-ink">Add or update a person</h2>
        <form action={upsertUser} className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-[13px] font-medium text-ink-soft">Work email</span>
            <input
              type="email"
              name="email"
              required
              placeholder="name@agency.org"
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-[15px] text-ink"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-[13px] font-medium text-ink-soft">Name</span>
            <input
              type="text"
              name="name"
              required
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-[15px] text-ink"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-[13px] font-medium text-ink-soft">Role</span>
            <select
              name="role"
              required
              defaultValue="staff"
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-[15px] text-ink"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {PERMISSIONS[r].label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-[13px] font-medium text-ink-soft">
              Caseworker record (optional)
            </span>
            <select
              name="caseworkerId"
              defaultValue=""
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-[15px] text-ink"
            >
              <option value="">None — no caseload of their own</option>
              {data.caseworkers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="sm:col-span-2">
            <legend className="mb-1 text-[13px] font-medium text-ink-soft">
              Team(s) — ignored for Executive
            </legend>
            <div className="flex flex-wrap gap-3">
              {data.teams.map((t) => (
                <label key={t.id} className="flex items-center gap-2 text-[14px] text-ink">
                  <input type="checkbox" name="teamIds" value={t.id} />
                  {t.name}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="sm:col-span-2">
            <button
              type="submit"
              className="rounded-lg bg-accent px-4 py-2 text-[14px] font-semibold text-white hover:opacity-90"
            >
              Save
            </button>
          </div>
        </form>
      </Card>

      <Card className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-[14px]">
            <thead>
              <tr className="text-[12px] uppercase tracking-wide text-muted">
                <th className="px-5 py-3 font-semibold">Name</th>
                <th className="px-5 py-3 font-semibold">Email</th>
                <th className="px-5 py-3 font-semibold">Role</th>
                <th className="px-5 py-3 font-semibold">Team(s)</th>
                <th className="px-5 py-3 font-semibold" />
              </tr>
            </thead>
            <tbody>
              {roster.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-6 text-center text-ink-soft">
                    No one is on the roster yet — no real email can sign in until it&rsquo;s
                    added above.
                  </td>
                </tr>
              ) : (
                roster.map((r) => (
                  <tr key={r.email} className="border-t border-line">
                    <td className="px-5 py-3 font-medium text-ink">{r.name}</td>
                    <td className="px-5 py-3 text-ink-soft">{r.email}</td>
                    <td className="px-5 py-3 text-ink-soft">{PERMISSIONS[r.role].label}</td>
                    <td className="px-5 py-3 text-ink-soft">
                      {r.teamIds.length
                        ? r.teamIds.map((id) => teamName.get(id) ?? id).join(", ")
                        : "Agency-wide"}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <form action={deleteUser}>
                        <input type="hidden" name="email" value={r.email} />
                        <button
                          type="submit"
                          className="text-[13px] font-medium text-risk hover:underline underline-offset-2"
                        >
                          Remove
                        </button>
                      </form>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <p className="mt-6 text-[13px] text-muted">
        This screen controls the roster, not sign-in itself — sign-in still uses the development
        accounts (see the banner above) until a real Google Workspace login is wired in. Once it
        is, a verified email that isn&rsquo;t on this list will be refused, not defaulted to any
        role.
      </p>
    </div>
  );
}
