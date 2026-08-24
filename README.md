# Milli — Casework Dashboard (Phase 1 scaffold)

A modern, role-based dashboard for a **Texas foster-care case-management agency**. It presents
casework data — cases, caseloads, and date-driven compliance obligations — tailored to three
audiences: **executives (CEO)**, **managers**, and **caseworkers (staff)**.

ExtendedReach stays the system of record. This app is a **presentation/analytics layer** on top of
it. See the strategy brief for why this "dashboard-on-top" approach was chosen over building a full
replacement.

Data reaches it through **scheduled Excel exports**, not an API. A read-only audit of the live
ExtendedReach tenant established that the system has no API on this plan and **no report-level
scheduling**, that the Zoho Analytics feed costs $500 + $125/month and was declined by the executive
team — and that it is unnecessary, because every metric this dashboard needs is reachable through
one-click Excel exports. `scripts/export-extendedreach.mjs` automates those clicks.
**Read [`docs/extendedreach-audit.md`](docs/extendedreach-audit.md) before changing the data path.**

> **Status: scaffold.** This is Phase 1 groundwork — the architecture, role model, data-access
> boundary, and UI are in place and run end-to-end on synthetic data. It is **not** production- or
> HIPAA-certified. The auth provider remains stubbed. The export data path is implemented but its
> column mappings need reconciling against one real workbook before they can be trusted
> (see [Open items](#open-items-phase-0)).

> **Scope: Foster Care only.** The agency runs seven programs, but only Foster Care is configured in
> ExtendedReach. The other six are tracked elsewhere and join in a later phase from their own
> sources.

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
      morning/           # four-tier morning triage board (docs/morning-board.md)
      training/          # staff training library — all roles, no case data
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
    triage.ts            # four-tier morning triage (act / approve / soon / decide)
    training.ts          # training library + strict Instagram permalink allowlist
    aging.ts             # day arithmetic + abandonment and due-soon cutoffs
    extendedreach/
      schema.ts          # per-report field/header aliases (source of truth)
      exports.ts         # parses exported .xlsx workbooks -> CaseworkDataset
      identity.ts        # name normalisation + stable pseudonymous ids
    zoho/
      client.ts          # the ONE data boundary (mock | exports | zoho)
      types.ts           # domain types the dashboard needs
      mock.ts            # synthetic fixtures + dev accounts
scripts/
  export-extendedreach.mjs  # Playwright exporter — clicks the Excel buttons
  inspect-export.ts         # reconciles a real workbook against schema.ts
middleware.ts            # edge guard: bounce unauthenticated requests to /login

The `zoho/` directory keeps its name for now to avoid churning imports; Zoho is
no longer the intended data path.
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
- A **signed BAA** with the hosting provider and every subprocessor touching PHI.
- A **HIPAA-eligible host** (AWS / GCP / Azure). Note: Vercel's default tier is not HIPAA-covered.
- Confirmation of **Texas DFPS** child-welfare data-handling requirements.

## Connecting live data

`DATA_SOURCE` selects one of three modes at the single boundary in `src/lib/zoho/client.ts`.
Everything downstream depends only on `getDataset()`, so switching modes changes nothing in the UI.

| Mode | Behaviour |
|---|---|
| `mock` (default) | Synthetic fixtures, no network. Use for development. |
| `exports` | **The intended production path.** Reads workbooks from `ER_EXPORT_DIR`. |
| `zoho` | The original Zoho Analytics plan. Retained but not recommended — declined on cost, and unnecessary. Still stubbed. |

To run against real exports:

```bash
node scripts/export-extendedreach.mjs --login   # once, interactive (MFA)
npm run export:er                               # pulls all ten reports
npm run inspect:export -- ./data/exports        # reconcile columns (do this first time)
DATA_SOURCE=exports npm run dev
```

`inspect:export` is the step that turns a mismatch from "the dashboard is
empty" into "add this alias to schema.ts". Its output masks names and
free-text, so it is safe to paste into a ticket.

See [`scripts/README.md`](scripts/README.md) for the exporter, and
[`docs/extendedreach-audit.md`](docs/extendedreach-audit.md) for which report feeds which metric.

## Open items (Phase 0)

1. ~~**ExtendedReach → Zoho Analytics feed (critical).**~~ **Answered** by the system audit — the
   feed costs $500 + $125/month, was declined, and is unnecessary. Replaced by the export path.
   See [`docs/extendedreach-audit.md`](docs/extendedreach-audit.md).
2. **Reconcile the export column mappings (blocking).** The header names in
   `src/lib/extendedreach/schema.ts` are the audit's best reading of each report. Run
   `npm run inspect:export -- ./data/exports` against real workbooks and add any missing header
   aliases it reports. Until this passes for every report, the data is not trustworthy.
3. **Ask the vendor for a Case ID column.** Every report identifies people by name only. With
   sibling groups already in the data, name-matching is the weakest link in the pipeline.
4. **Ratify the abandoned-record cutoff.** ~Half of 1,351 past-due items date from 2020–2023.
   `ER_ABANDONED_AFTER_DAYS` defaults to 365; the exec team should confirm it before the figure is
   reported anywhere.
5. **Hosting & BAA ownership** — we-host (vendor) vs. customer-hosts. Deferred.
6. **Does PHI need to leave ExtendedReach at all,** or can sensitive fields stay masked/aggregated?
7. **Exact role data definitions** (minimum necessary per role).
8. **Texas-specific DFPS rules** the agency is contractually held to.

---

_Synthetic data only in this repo. Do not commit real PHI or secrets._
