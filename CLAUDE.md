# milli — working notes for Claude

Role-based casework dashboard for a Texas foster-care agency, reading
ExtendedReach data through scheduled Excel exports.

## How the user wants to work

**Ask hard questions rather than assuming, and push back when something looks
wrong.** This was requested explicitly. Concretely:

- When a decision has a risk the user may not have considered, say so plainly
  once, explain the mechanism, and offer the safer path — do not just comply.
  This has already mattered twice: the Zoho feed the audit showed was
  unnecessary, and a plan to put real children's records on a public URL.
- Prefer a direct question over a guess when the answer changes the work.
- Correct factual misunderstandings even when they are the user's stated
  reason for a decision. "Only I open it on this device" was a genuine
  misreading of how public hosting works, and saying so changed the outcome.
- The user is not a developer. Explain terms the first time (they asked what a
  pull request is). Do not assume a terminal is available to them — offer the
  lowest-effort path that gets the same answer.
- Verify claims rather than asserting them. Every "this is safe" or "this
  works" in this repo should be backed by something that was actually run.

## Hard rules for this project

**This is children's PHI.** Names, placements, medications, court dates.

1. **Never put real records on the Netlify demo.** `houstonstrongcpa.netlify.app`
   is public to the internet, authentication is stubbed (any visitor can sign in
   as CEO), and Netlify signs no BAA. `netlify.toml` pins `DATA_SOURCE=mock`;
   leave it pinned.
2. **De-identify before sharing anything derived from real exports** —
   `npm run deidentify`. It preserves every statistic and replaces every name.
3. **Never print client names in chat, commits, PRs, or artifacts.** Use IDs,
   initials, or aggregates. `npm run inspect:export` masks by default.
4. Real exports live in `./data/exports` and are gitignored. So is
   `.er-session.json`, which is an authenticated credential.

## Project facts established so far

- **ExtendedReach has no API and no report scheduling** on this plan. Data
  leaves via one-click Excel exports only — no CSV anywhere. See
  `docs/extendedreach-audit.md`, which is the record of the system audit.
- **The Zoho Analytics feed was declined** ($500 + $125/mo) and is unnecessary.
  The `zoho` data-source mode is retained but dead; `exports` is the live path.
  The `src/lib/zoho/` directory keeps its name only to avoid import churn.
- **Only Foster Care is configured** in ExtendedReach. The agency runs seven
  programs; the other six are tracked elsewhere and are a later phase.
- **The `Worker` column means "entered by", not "assigned to."** Never present
  it as caseload. True caseload comes from `V_CASELOADS_WKR_MONTH-C`.
- **`Submitted` is not overdue.** 165 of 997 past-due items are finished work
  awaiting supervisor approval; counting them overstates the backlog and makes
  staff look delinquent for work they completed.
- **`Due Soon/Past Due` is a filtered view of `In Process`** — 98.4% overlap.
  Ingesting both without deduping inflates the backlog by roughly half. The
  loader keys on subject + type + due date.
- **`Case #` exists** on the open-cases roster and is the case id. The older
  note that no stable identifier exists is wrong.
- **The open-cases roster carries DOB, SSN, Medicaid # and Customer #.** It is
  the most sensitive export; `schema.ts` declares per-field sensitivity and the
  de-identifier replaces identifiers and shifts birth dates.
- **`caseload` is a cross-tab**, not rows: `[year|worker|program] Name Jan…Dec`
  with 0/1 flags. Caseload for a month is a column sum. It is also the only
  source of trend history.
- Verified real figures: 52 open cases, 43 workers, 2,766 distinct obligations,
  1,556 overdue (902 actionable, 654 over a year), 181 due soon, ~35% on-time,
  active caseload 54–64 across 2026.
- **The approval queue is the harder bottleneck.** 394 submissions await
  approval; 18 approvers hold them, and **one holds 202 (51%)**. Casework load
  concentrates (top worker 29% of open tasks); approval load concentrates twice
  as hard. Adding caseworker capacity does not drain it.
- **`Performed By` is a real performer column** — unlike `Worker`. It appears on
  Awaiting Approval and Rejected. Still per-item attribution, still not caseload.
- **Not every export is Excel.** Compliance Tracking and Reports Completed by
  Date arrive as CSV, and the Compliance CSV is Windows-1252, not UTF-8. The
  reader handles both; the audit's "Excel only" holds for report views only.
- **Compliance Tracking is a matrix** — 52 cases × 76 obligation columns, not a
  row per task. Parsed by `MatrixReportSpec`, deliberately **not** loaded into
  the dashboard: it would quadruple every headline number. Exec decision first.

## Commands

```bash
npm run dev                                # mock data
npm run export:er                          # pull reports from ExtendedReach
npm run inspect:export -- ./data/exports   # reconcile columns; masked output
                                           # reads .xlsx and .csv
npm run deidentify -- ./real --out ./data/exports   # all files in ONE run
DATA_SOURCE=exports npm run dev            # real (or de-identified) data
npm run build && npx tsc --noEmit          # before any push
```

## Still open

- Authentication is stubbed. Production needs a real IdP and a HIPAA-eligible
  host — Netlify and Vercel default tiers are neither.
- Column mappings verified for five reports: `pastdue_case`,
  `needapproval_case`, `rejected_case`, `reportscompleted`, `compliance_case`.
  Still unverified — no export seen yet: `opencases`, `pastdue_home`,
  `inprocess`, `completions`, `caseload`, `ontime`, `openbeds`, `nextcourt`,
  `staffexp`.
- `needapproval_case`, `rejected_case`, `reportscompleted` and
  `compliance_case` parse but are **not wired into the dataset** — only
  `pastdue_case`, `pastdue_home`, `inprocess`, `opencases` and `caseload` are.
- Ask the vendor for a Case ID column. Names are the only join key today, and
  the data contains sibling groups.
