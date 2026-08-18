import { signIn } from "@/app/actions";
import { listMockAccounts } from "@/lib/auth";
import { PERMISSIONS } from "@/lib/rbac";

export default function LoginPage() {
  const accounts = listMockAccounts();

  return (
    <main className="min-h-screen grid place-items-center px-6 py-16">
      <div className="w-full max-w-md">
        <div className="mb-8">
          <div className="text-[13px] font-semibold tracking-[0.14em] uppercase text-accent">
            Milli
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            Casework Dashboard
          </h1>
          <p className="mt-2 text-[15px] text-ink-soft">
            Sign in to continue. This build uses{" "}
            <span className="font-medium text-ink">development accounts</span> — replace with your
            organization&rsquo;s single sign-on before handling real records.
          </p>
        </div>

        <form action={signIn} className="rounded-2xl border border-line bg-surface p-2 shadow-sm">
          <ul className="flex flex-col">
            {accounts.map((a) => (
              <li key={a.id}>
                <button
                  type="submit"
                  name="userId"
                  value={a.id}
                  className="flex w-full items-center justify-between gap-4 rounded-xl px-4 py-3 text-left hover:bg-surface-2 focus-visible:bg-surface-2"
                >
                  <span>
                    <span className="block text-[15px] font-medium text-ink">{a.name}</span>
                    <span className="block text-[13px] text-muted">
                      {a.teamIds.length ? a.teamIds.join(", ") : "Agency-wide"}
                    </span>
                  </span>
                  <span className="rounded-full bg-accent-soft px-2.5 py-1 text-[12px] font-semibold uppercase tracking-wide text-accent">
                    {PERMISSIONS[a.role].label}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </form>

        <p className="mt-6 text-[13px] text-muted">
          Synthetic data only. No real PHI is present in this environment.
        </p>
      </div>
    </main>
  );
}
