# Milli — Casework Dashboard (Phase 1 scaffold)

A modern, role-based dashboard for a **Texas foster-care case-management agency**. It presents
casework data — cases, caseloads, and date-driven compliance obligations — tailored to three
audiences: **executives (CEO)**, **managers**, and **caseworkers (staff)**.

ExtendedReach stays the system of record. This app is a **presentation/analytics layer** on top of
it, reading data through **Zoho Analytics** (the agency's only confirmed data tap). See the strategy
brief for why this "dashboard-on-top" approach was chosen over building a full replacement.

> **Status: scaffold.** This is Phase 1 groundwork — the architecture, role model, data-access
> boundary, and UI are in place and run end-to-end on synthetic data. It is **not** production- or
> HIPAA-certified. The auth provider and the live Zoho query path are deliberately stubbed pending
> Phase 0 confirmation (see [Open items](#open-items-phase-0)).

---

## Quick start

```bash
npm install
cp .env.example .env.local   # DATA_SOURCE=mock works out of the box
npm run dev                  # http://localhost:3000
```

The dev build ships **synthetic data** and a **development sign-in** (one account per role) so you
can exercise the role-based views immediately. No real data or secrets are required to run it.

Scripts: `npm run dev` · `npm run build` · `npm run start` · `npm run lint` · `npm run typecheck`.

## Tech stack

- **Next.js 15** (App Router, React 19, TypeScript, server components)
- **Tailwind CSS** with a themed token palette (light/dark), carried over from the strategy brief
- No external UI or chart libraries — components and the trend chart are hand-built (inline SVG)

## How it's organized

```
src/
  app/
    (app)/               # authenticated shell + pages
      layout.tsx         # sidebar, role-aware nav, demo-mode banner
      dashboard/         # role-routed overview (KPIs, trend, needs-attention)
      caseload/          # scoped case list
      compliance/        # compliance register (CEO + managers only)
    login/               # dev sign-in (one account per role)
    actions.ts           # sign-in / sign-out server actions
  components/            # Card, KpiCard, ComplianceBadge, TrendChart
  lib/
    rbac.ts              # roles, permissions, and DATA SCOPING (source of truth)
    auth.ts              # session cookie — DEV/MOCK, swap for a real IdP
    audit.ts             # PHI-access audit logging
    metrics.ts           # role-scoped aggregation over the dataset
    zoho/
      client.ts          # the ONE data boundary (mock | live Zoho Analytics)
      types.ts           # domain types the dashboard needs
      mock.ts            # synthetic fixtures + dev accounts
middleware.ts            # edge guard: bounce unauthenticated requests to /login
```

## Roles and access

Access is enforced by **data scoping on the server**, not just hidden in the UI — the "minimum
necessary" principle. `scopeForUser()` in `src/lib/rbac.ts` is the single source of truth:

| Role | Sees | Can open |
|---|---|---|
| **CEO** | All cases, agency-wide KPIs, 12-month trend, per-worker caseloads | Overview, Caseload, Compliance |
| **Manager** | Cases across their team(s) | Overview, Caseload, Compliance |
| **Staff** | Only their own assigned caseload | Overview, Caseload |

Every server-side read passes the dataset through `scopeDataset()` so out-of-scope records never
reach the browser. Staff hitting the compliance route are redirected and the attempt is audited.

## Compliance posture (what's built vs. what's pending)

This scaffold bakes in patterns a PHI app needs, but **operating it under HIPAA requires more than
code** — a signed BAA, a hardened host, and policy. What's in place:

- **Data scoping** as the access-control primitive (minimum necessary).
- **Audit logging** of PHI access (`src/lib/audit.ts`) — who, what action, which record ids, when.
  Identifiers only; never PHI values. Dev writes to stdout; point `AUDIT_SINK` at a durable,
  tamper-evident store in production.
- **Security headers** (`next.config.mjs`): HSTS, `X-Frame-Options: DENY`, `nosniff`,
  `Referrer-Policy: no-referrer`.
- **Secrets/PHI kept out of git** (`.gitignore` covers `.env*.local`, logs).
- **PHI minimization** — broad views use a non-PHI `displayId`; names appear only in the scoped
  caseload where the task requires them.

Still required before any real data (not code — process + infra):

- A **BAA-capable identity provider** replacing the mock auth in `src/lib/auth.ts`.
- A **signed BAA** with the hosting provider and every subprocessor touching PHI (Zoho included).
- A **HIPAA-eligible host** (AWS / GCP / Azure). Note: Vercel's default tier is not HIPAA-covered.
- Confirmation of **Texas DFPS** child-welfare data-handling requirements.

## Connecting live data

Set `DATA_SOURCE=zoho` and fill in the `ZOHO_*` vars in `.env.local`. The live query path in
`src/lib/zoho/client.ts` is stubbed with the exact TODOs — it throws a clear error until Phase 0
confirms the workspace/view names and OAuth credentials. Everything downstream depends only on
`getDataset()`, so switching from mock to live changes nothing in the UI.

## Open items (Phase 0)

1. **ExtendedReach → Zoho Analytics feed (critical).** Confirm it exists, the plan upgrade required,
   its cost, refresh frequency, and exactly which fields/reports are exposed. Everything depends on
   this — answer it before further build investment.
2. **Hosting & BAA ownership** — we-host (vendor) vs. customer-hosts. Deferred.
3. **Does PHI need to leave Zoho at all,** or can sensitive fields stay masked/aggregated?
4. **Exact role data definitions** (minimum necessary per role).
5. **Texas-specific DFPS rules** the agency is contractually held to.

---

_Synthetic data only in this repo. Do not commit real PHI or secrets._
