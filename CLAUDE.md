# milli — working notes for Claude

Role-based casework dashboard for a Texas foster-care agency, reading
ExtendedReach data through scheduled Excel exports.

## How the user wants to work

**Ask hard questions rather than assuming, and push back when something looks
wrong.** This was requested explicitly. Concretely:

- When a decision has a risk the user may not have considered, say so plainly
  once, explain the mechanism, and offer the safer path — do not just comply.
  This has already mattered three times: the Zoho feed the audit showed was
  unnecessary, a plan to put real children's records on a public URL, and real
  PHI landing hourly in a personal Gmail Drive folder with no possible BAA.
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
   initials, or aggregates. `npm run inspect:export` masks by default. This is
   not a demo-only rule — it applies exactly as much to the real production
   build (2026-09-02: user confirmed agency authorization to proceed with the
   real system) as to the public Netlify demo. IDs-not-names is a display
   convention, not the `deidentify` synthetic-name pipeline (rule 2), which is
   specific to the public demo; this rule stands regardless of which one is
   in play.
4. Real exports live in `./data/exports` and are gitignored. So is
   `.er-session.json`, which is an authenticated credential.
5. **Run `npm run verify:deidentified -- <dir>` before publishing anything.**
   It checks every column of every file and exits non-zero on any unscrubbed
   name. The de-identifier's own report cannot catch this class of mistake —
   it counts what it replaced, not what it never looked at.
6. **A personal `@gmail.com` account cannot hold real PHI compliantly.**
   Google only offers a HIPAA BAA to Google Workspace accounts — a consumer
   Gmail/Drive account has no BAA option at all, regardless of folder sharing
   settings, and Drive full-text-indexes file contents so anything with query
   access to a folder can retrieve real names via search without opening the
   file. A separate hourly automation (outside this repo) currently writes
   real ExtendedReach exports into such a personal-account Drive folder — this
   was flagged to the user 2026-09-02 and they chose to keep it running while
   handling storage separately. Don't build more on top of that folder as if
   it were compliant storage; treat every file in it as PHI with no BAA
   coverage until it moves to a Workspace account (or elsewhere with one).

## Project facts established so far

- **2026-09-02: this is now a real, agency-authorized production build**, not
  just a stakeholder demo. The user confirmed the agency has given permission
  to proceed and wants the system agency-managed. The Netlify-demo /
  `deidentify`-pipeline discussion (hard rules 1–2) is specific to that one
  public demo site and does not need to be re-raised for internal production
  build decisions — the user asked for this explicitly and it's settled. What
  does NOT change: hard rule 3 (no raw PHI names in chat/commits/PRs/
  artifacts) — that's a blanket rule about Claude's own outputs, unrelated to
  which deployment target is being discussed.
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
  1,556 overdue (902 actionable, 654 over a year), 181 due soon, 41.1% on-time
  across 3,184 completed items, active caseload 54–64 across 2026.
- **De-identify every report in ONE run.** Free text in one report names people
  who appear as name columns only in another; the synthetic map must be global.
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
- **The morning board is four tiers, cut by who acts next** — act today /
  waiting on approval / due soon / needs a decision. See
  `docs/morning-board.md`. Tiers 1, 3 and 4 partition the backlog and may be
  added up; **tier 2 is a different population and must never be summed with
  them.** Reconciles exactly to the audit at a pinned date: 902 / 654 / 181.
- **`scopeDataset` was dropping 1,627 of 2,766 obligations for the CEO** — it
  applied the case join to agency-wide scopes as though it were a permission
  filter, so the UI showed roughly half the backlog the loader had measured.
  Fixed. Team and personal scopes still narrow via the join, because an
  obligation joining to no case cannot be attributed to a worker.
- **`Scheduled` and `Event` rows carry dates but cannot be late.** Flagged
  `calendarOnly` at load. Anything that ages items by due date must skip them
  or every past calendar entry lands in the backlog.
- **The task `type` column carries people's names.** Certification items are
  named after the person: `SIDS Expires (<given>)`, `Child Logs (<given>,
  <given>)` for sibling groups. It was declared sensitive in no report, so 55
  real given names across 170 rows reached the public repo and the public
  demo. `type` is now free text everywhere and the scrubber has a
  parenthetical backstop. **Assume any column can contain a name until
  checked.**
- **The training library is self-hosted where possible.** `/training` is open
  to every role and carries no case data. Entries are either `file` (served
  from `public/training`, nothing third-party contacted at all — preferred) or
  `instagram` (a permalink, kept **click-to-load** so nothing reaches Meta
  until a user presses play; an embed firing on page load would send a
  referrer from a PHI app to a company that signs no BAA). `embedUrlFor()` is
  an allowlist and is the only thing between the config and an arbitrary
  framed origin; keep it strict if the library ever becomes data-driven.
  **Never turn an `instagram` entry into a `file` one by downloading the
  media** — that is redistributing a platform copy, and it outlives an
  upstream deletion. Re-hosting is only right for recordings the agency
  supplies directly, as these two were.
- **Screen recordings get watched before they are published.** All three
  training clips were frame-checked for children, faces and legible client
  paperwork before being committed. Two were clean. The third closed on a
  young participant waving to camera and was **trimmed from 9.7s to 8.2s** —
  not because the footage is sensitive (it is public on the agency's own
  account) but because a minor's face inside a foster-care casework demo
  implies they are a child in care, and a marketing release is not consent to
  appear in a product demo. Audio was NOT verifiable here — no transcription
  available — so a spoken name remains unchecked in all three.
- **Holder attribution never uses `Worker`.** Tier 2 is held by `Submit To`;
  the other tiers by the case's assigned worker from the open-cases roster.
  Items naming nobody are counted in totals but excluded from the ranking, and
  the excluded count is shown.

## Commands

```bash
npm run verify:deidentified -- ./data/demo # BEFORE publishing; exits 1 on a name
npm run dev                                # mock data
npm run export:er                          # pull reports from ExtendedReach
npm run inspect:export -- ./data/exports   # reconcile columns; masked output
                                           # reads .xlsx and .csv
npm run split:workbook -- <combined.xlsx>  # split a Drive-style combined
                                           # workbook into per-slug files first
npm run deidentify -- ./real --out ./data/exports   # all files in ONE run
DATA_SOURCE=exports npm run dev            # real (or de-identified) data
npm run build && npx tsc --noEmit          # before any push
```

## Deploying the demo

The Netlify site builds from `main` on push. Three things have each broken it
once and are easy to re-break:

- **`netlify.toml` `[build.environment]` does not reach the runtime.** The
  Next server is a Netlify Function reading `process.env` per request. The
  vars that decide what the site serves are the **site** environment
  variables (`DATA_SOURCE=exports`, `ER_EXPORT_DIR=./data/demo`).
- **`data/demo` only reaches the function via `outputFileTracingIncludes`**
  in `next.config.mjs`, because the loader's path is a runtime value that
  file tracing cannot follow.
- **Linking the repo does not build what is already pushed.** Netlify builds
  on the next push webhook; use "Trigger deploy" for anything earlier.

If exports are unreachable the app degrades to synthetic data rather than
failing, and the banner states which mode is live — so "the demo shows the
wrong numbers" is always visible on the page, never silent.

## Still open

- Authentication is stubbed. Production needs a real IdP and a HIPAA-eligible
  host — Netlify and Vercel default tiers are neither.
- **2026-09-02: added `/admin/users`, a CEO-only "Manage Users" screen**,
  because Google Workspace SSO (once wired up) only proves *identity* — it
  does not decide who gets a dashboard account or what role/team they see.
  Backed by `src/lib/roster.ts`: an explicit email -> role -> teamIds ->
  caseworkerId list, edited from the UI, gated by the existing
  `manageUsers` permission (CEO only). `resolveRosterUser(email)` is the
  seam a real SSO callback should call before issuing a session — an email
  Google can verify but that isn't on this roster must be refused, not
  defaulted to any role. **Storage is a local JSON file
  (`./data/roster.json`, gitignored) — explicitly a placeholder.** Cloud
  Run instances don't share or persist local disk, so this must move to a
  durable store (a DB row, Firestore) before real production use; it is
  fine for local/dev use in the meantime. Verified in the browser via
  Playwright: CEO can add/remove roster entries, and a staff account is
  redirected away from `/admin/users`.
- Column mappings verified for nine reports: `pastdue_case`,
  `needapproval_case`, `rejected_case`, `reportscompleted`, `compliance_case`,
  `opencases`, `pastdue_home`, `caseload`, `ontime`. Also now verified,
  2026-09-02, against a real export pulled from the hourly Drive automation
  (see the Gmail/BAA note in Hard Rules): `openbeds` — its `worker` column is
  headed "Home Worker", not "Worker" (added as an alias), and `bedsAvailable`
  values look like `"1 of 2"` (parses fine as-is: `parseInt` reads the leading
  number, which is beds *available*, not capacity — the "of N" half is
  currently discarded). `opencases`'s `removalDate` column came through as the
  literal text `document.write(removalViewName);` in that export — a broken
  cell from that automation's pull, not a real header to alias. Still
  unverified — no export seen yet: `inprocess`, `completions`, `nextcourt`,
  `staffexp`.
- **`openbeds` is now wired into the dataset** as `CaseworkDataset.homes`, and
  has its own page at `/homes` (permission `viewHomesRegister`, same
  ceo/manager-only default as compliance). Deliberately thin: the export also
  carries the home's address, phone, and an `Active Placements` column naming
  the children currently there; none of it is modelled or shown — a capacity
  register doesn't need it, and it's the same minimum-necessary call the rest
  of this app makes.
- **The "Foster Homes / Recruitment / Placements / Monthly Data" dashboard the
  user asked to replicate does not match what ExtendedReach actually exports.**
  `openbeds` covers home capacity; nothing in the export set covers a
  recruitment pipeline, a children roster, placement history, or a monthly
  rollup sheet — those aren't ExtendedReach report views on this plan. Built
  `/homes` from `openbeds` (real capacity data) rather than fabricating the
  other tabs against no data source. Ask the vendor, or find whichever system
  actually tracks recruitment, before building those.
- **A combined multi-sheet workbook (e.g. from the Drive automation) needs
  `npm run split:workbook` before `inspect:export`/the loader can read it** —
  see `scripts/README.md`. Splitting **11** real sheets from a 2026-09-02
  export matched **11/11** known report slugs cleanly.
- **Nothing yet moves Drive → the live Netlify dashboard automatically.** The
  deployed site reads `ER_EXPORT_DIR` from local disk at request time; it has
  no Google Drive access of its own. "Hourly to Drive" and "updates production"
  are two different systems today — see `scripts/README.md` for what closing
  that gap needs (a scheduled job with real Drive API credentials, writing
  into wherever the deploy reads from).
- `needapproval_case` **is now wired** — it is the only source of the approver
  (`Submit To`) that tier 2 needs. Deduped against Submitted rows already
  ingested from the task reports, keyed subject + type; the count lands in
  `diagnostics.approvalsDeduplicated`. No such export exists in `data/demo`
  yet, so the demo shows tier 2 without the approver breakdown and says so.
  Verified against a synthetic export: 66 of 208 rows merged, and tiers 1/3/4
  did not move.
- `rejected_case`, `reportscompleted` and `compliance_case` parse but are
  still **not wired into the dataset**.
- The dev sign-in accounts are mock-specific (`cw-1`…`cw-8`, `t-north`), so
  under `DATA_SOURCE=exports` they match no worker or team and every non-CEO
  role scoped to zero. `src/lib/demo-roles.ts` now binds them to real workers
  when — and only when — the signed-in account is one of `MOCK_USERS`. That
  gate is self-limiting: a real IdP stops returning those accounts and the
  binding becomes unreachable. **It widens scope, so delete the module with
  the auth stub.** The UI names the workers an account was bound to.
- `npm run lint` cannot run — the repo has no ESLint config, so `next lint`
  drops into its interactive setup. The gates that do work are
  `npm run build` and `npx tsc --noEmit`.
- Ask the vendor for a Case ID column. Names are the only join key today, and
  the data contains sibling groups.
