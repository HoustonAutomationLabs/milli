# ExtendedReach system audit

_Read-only walkthrough of every Reports, Rosters, Tasks and Administration screen
in the agency's live ExtendedReach tenant._

This document answers **Phase 0 item #1** in the README — _"ExtendedReach → Zoho
Analytics feed (critical). Confirm it exists, the plan upgrade required, its
cost, refresh frequency, and exactly which fields/reports are exposed."_

**Answer: the feed exists, costs $500 setup + $125/month, and the executive team
declined it. It is also unnecessary.** Every metric this dashboard needs is
reachable through report exports the agency already has.

No client names, dates of birth, case details or health data were recorded
during the audit — only report names, locations, column headers and structural
metadata. No Save/Export/Schedule/Delete action was triggered.

---

## Findings that changed the architecture

### 1. No report can email or schedule itself

There is **no subscribe, schedule or recurring-delivery control on any report**
in the system. The original plan — have ExtendedReach email a nightly CSV to an
inbox — cannot work.

The closest equivalent is **Administration → Organization Settings → Email
Alerts**, an org-wide rule engine with 35+ active rules, several of them
due-date driven ("Service Plan Due in 14 Days", "CANS Assessment Overdue",
"Variance Expires in 30 Days"). It is rule-based, not report-based, so it
cannot replace an export — but it can push events between refreshes.

### 2. Excel only — no CSV anywhere

Every exportable report offers **Excel and nothing else**. Two reports (Daily
Census by Program, Treatment Goals by Caseworker) offer no export at all. This
is why the reader in `src/lib/extendedreach/exports.ts` parses `.xlsx` rather
than the CSV originally assumed.

### 3. Only one program is configured

**Administration → Program Settings → Programs lists exactly one program:
Foster Care.** The Configurator confirms it — all 255 configured item types
split only between "Foster Care" (103) and "Home" (152).

The agency runs seven programs. The other six — Strong Smart Innovation Center,
Internships & Education, Prevention Services, Hospital Sitting, Adoption, Case
Management — have **no program record and no reports** here. Adoption exists
only as fields on a Foster Care case (Adoption Referral date, Adoption Worker)
and as a Foster Care sub-category, not as a program.

**Scope consequence:** this dashboard covers Foster Care. The other six join in
a later phase from their own data sources, which are outside ExtendedReach.

### 4. No stable identifiers

No report exposes a Case ID, Child ID or Worker ID. Every view identifies people
by **name only**, in `"Last, First"` form. The data already contains sibling
groups — several sets of siblings share a surname — so name matching will
eventually collide,
and a single typo breaks a join.

`src/lib/extendedreach/identity.ts` works around this by normalising names
aggressively and deriving stable pseudonymous ids. **Ask the vendor to add a
Case ID column to the key views** — it removes the weakest link in the pipeline
and the whole module with it.

---

## The operational finding

ExtendedReach's own reporting puts the agency's position at:

| Measure | Value | Source |
|---|---|---|
| On-time task completion | **~35%** | `V_MONTHVAR-C` |
| Case tasks past due | **997** | `V_TASKS_INPROC_PASTDUEBYDATE-C` |
| Home tasks past due | **354** | `V_HOMETASKS_INPROC_PASTDUEBYDATE-C` |
| Due in next 30 days | **181** | same two reports |
| Cumulative non-compliant items | **7,626** | `V_MONTHNC-C` |

That is a **7.5:1 backlog-to-pipeline ratio** and roughly two of every three
tasks completed late.

Leadership estimates about **half the past-due items are abandoned records**
open since 2020–2023, which would leave ~675 genuinely actionable items (~3.7:1,
around 75 per caseworker). The loader does not assume this: it age-buckets every
overdue item so the abandoned share is **measured**, with the cutoff set by
`ER_ABANDONED_AFTER_DAYS` (default 365).

> This is a staffing and process problem, not a reporting problem. The dashboard
> makes it visible every morning; it does not fix it.

---

## Verified against a real export

`V_TASKS_INPROC_PASTDUEBYDATE-C` was exported and run through
`npm run inspect:export`. **All seven columns resolved on the first attempt** —
`Date | Status | Type | Worker | Client | Program | Description` — and the row
counts reconcile exactly with the screen reading: 1,161 rows, **997 past due,
164 upcoming**.

Three things the real file changed:

**1. The abandoned share is 31%, not ~50%.** Age of the 997 past-due items:

| Age | Count | Share |
|---|---|---|
| 0–30 days | 181 | 18% |
| 31–90 days | 209 | 21% |
| 91–365 days | 296 | 30% |
| **Over 1 year** | **311** | **31%** |

Of those, 115 are more than two years old and the oldest is 6.4 years. So the
working assumption was too optimistic: **686 items are under a year old**, not
the ~500 a half-and-half split implied.

**2. Status is not what the screen suggested.** The report groups visually into
"Past Due" and "Due in Next 30 Days", but the exported `Status` column carries
the task's own state: Due (784), Submitted (166), Draft (148), Expires (50),
Rejected (6), Scheduled (6), Event (1).

This matters. **165 of the 997 past-due items are already Submitted** — finished
work sitting with a supervisor for approval. Counting them as overdue overstates
the backlog and shows staff as delinquent for work they completed. `classify()`
(then named `stateFor()`) treats Submitted as satisfied. Netting them out:

- Genuinely outstanding: **832**
- Of which actionable (under a year): **590**
- Of which abandoned (over a year): **242**

**3. The organisation is larger than the completion sample suggested.** This
report names **32 distinct workers** and **151 distinct clients** with open
tasks, across **62 task types**. The August completion sample showed only 9
workers because that column records who *entered* an item in one month, not who
carries the caseload — further confirmation of the entered-by finding below.

Workload remains concentrated: the top worker holds 338 of 1,161 open tasks
(29%), and the top four hold 65%.

---

## Second export run — four more reports verified

_2026-08-22. Four further exports were run through `npm run inspect:export`.
All four resolved; `pastdue_case` was re-run unchanged and still reconciles at
1,161 rows._

| Report | View | Rows | Result |
|---|---|---|---|
| Awaiting Approval | `V_REPORTS_NEEDAPPROVAL-C` | 394 | ✓ all 8 columns |
| Rejected | `V_TASKS_REJECTED-C` | 8 | ✓ all 9 columns |
| Reports Completed by Date | `V_ALLBYCOMPLETION_REPORTS-C` | 145 | ✓ all 6 columns |
| Compliance Tracking | `A_COMPLIANCE_CASES` | 52 × 76 | ✓ all 3,952 cells |

Four things these files changed.

### 1. Two of them are CSV — "Excel only" is not the whole picture

The audit recorded that every exportable report offers Excel and nothing else.
That holds for the report views in the Reports/Rosters/Tasks menus. It does not
hold for everything: **Compliance Tracking and Reports Completed by Date both
arrived as `.csv`**, and the Compliance CSV is Windows-1252 rather than UTF-8 —
a cp1252 apostrophe in one column header decodes to `U+FFFD` under UTF-8, which
would make that header unmatchable by the very reconciliation that has to match
it.

The reader now accepts both formats and both encodings
(`src/lib/extendedreach/grid.ts`), and the exporter no longer assumes a
downloaded file is `.xlsx` just because the control was labelled "Excel".

**Worth confirming with the agency:** whether those two files came out of
ExtendedReach as CSV directly, or were converted after download. The answer
changes whether the automated exporter can fetch them unattended.

### 2. The approval queue is a bigger bottleneck than the backlog suggests

`pastdue_case` showed that 165 of the 997 past-due items were already
`Submitted` — finished work awaiting a supervisor. The Awaiting Approval report
is where all such items live, past due or not, and it holds **394 submissions**
against **90 clients**, performed by **28 staff**.

The distribution is the finding. Those 394 items are queued to **18 approvers**,
and **one of them holds 202 — 51% of the entire approval queue.** The next
holds 74. Casework load concentrates in this agency (top worker 29% of open
tasks); approval load concentrates twice as hard.

This is a different problem from the past-due backlog and has a different fix.
Adding caseworker capacity does not drain a queue that is waiting on one
approver.

### 3. "Performed By" is a real performer column — unlike `Worker`

The Awaiting Approval and Rejected reports carry **`Performed By`** and
**`Submit To`** rather than `Worker`. `Performed By` names who actually did the
work, which the `Worker` column on the task reports does not (it records who
*entered* the item).

This is a genuine header mismatch of the kind `inspect:export` exists to catch:
`Performed By` was not in any alias list, and without it both reports would have
loaded zero rows with no indication why.

`Performed By` is still **not a caseload figure.** It is per-item attribution.
True caseload remains `V_CASELOADS_WKR_MONTH-C`.

The Rejected report also labels its date column **`Rejected`**, not `Date`.

### 4. Compliance Tracking is a matrix, not a list

Every other export is one row per obligation. Compliance Tracking is **one row
per case and one column per obligation type** — 52 cases by 76 items, every
cell filled — and the obligation names are data drawn from the agency's
Configurator, not a fixed schema. `ReportSpec` cannot describe that shape, so
`MatrixReportSpec` was added alongside it: it pins only the four leading
identity columns (`Case`, `Case Manager`, `Sec. Worker`, `Current Placement`)
and unpivots everything to their right.

The complete cell vocabulary across all 3,952 cells:

| Cell form | Count | Reads as |
|---|---|---|
| a bare date | 2,209 | done on that date |
| `Optional` | 637 | not applicable to this case |
| `<date> (Due)` | 389 | due |
| `Missing` | 283 | **never provided** |
| `<date> (Overdue)` | 264 | overdue |
| `<date> (Expires)` | 104 | due |
| `<date> (Expired)` | 27 | overdue |
| `<date> (In Proc.)` | 21 | in progress |
| `<date> (Submitted)` | 16 | awaiting approval |
| `<date> (Sched.)` | 2 | scheduled |

Netting out: **574 compliance gaps** (Missing + Overdue + Expired) and **514
items due**, across 52 cases — a mean of 11 open compliance items per case.

`Submitted` is treated as satisfied here exactly as it is in `stateFor()`, for
the same reason. `Missing` is the one judgement call: it carries no date, so it
cannot be aged, but it means a required document has never been provided. It
counts as a gap and will never appear in an age bucket — which is the honest
representation rather than dropping it or inventing a date for it.

**Not yet wired into the dashboard.** Loading 3,952 matrix obligations
alongside 1,161 tasks would more than quadruple every headline compliance
number without the figures meaning the same thing. That is a decision for the
exec team, not a silent side effect of adding a parser.

---

## Five more exports verified

`opencases`, `pastdue_home`, `inprocess`, `nextcourt` and `caseload` were
exported and run through `inspect:export`. Three matched first time; two did
not, and both were structural rather than a wording difference. Four findings
changed the code.

### 1. `Case #` exists after all

The audit concluded no report exposes a stable identifier. **The open-cases
roster carries `Case #`, populated for all 52 rows.** It is now the case id,
replacing the hash-of-the-name fallback — it survives spelling drift and tells
siblings apart, which name matching cannot. The request to the vendor for an id
column can be dropped.

### 2. That roster is the most sensitive file in the set

29 columns, including **`DOB` for every child, `SSN` for 16, `Medicaid #` for
44, and `Customer #` for 50**, alongside Race and Gender. The task reports
carry nothing like this. Two consequences:

- The raw file deserves more care than the others — it is a direct-identifier
  set, not just a name list.
- De-identification cannot be name-substitution alone. `schema.ts` now declares
  sensitivity per field, and identifiers are replaced with same-shaped
  synthetic values while dates of birth are shifted by a per-person offset of
  up to ±180 days, which keeps 43 of 52 children in the same three-year age
  band while making every exact date wrong.

Also in that report: **`Current Placement` holds the foster parents' names**,
not a placement category — 26 of 26 distinct values are person names. The
category is in the separate `Placement Type` column. It is now treated as PII.

### 3. `Due Soon/Past Due` and `In Process` are the same tasks

**1,139 of 1,157 past-due obligations — 98.4% — also appear in In Process.**
The former is a filtered view of the latter, not additional work. Ingesting
both naively produced 3,534 obligations where there are 2,395; the loader now
keys on subject + type + due date and skips repeats, reporting the count in
`diagnostics.deduplicated`.

This is the single largest correction so far. Left in place it would have
inflated the reported backlog by roughly half.

### 4. `caseload` is a cross-tab

Not one row per record. The shape is:

```
[year] | [worker] | [program] | Name | Jan | Feb | … | Dec
```

with the first three columns unlabelled and one row per (year, worker, client).
The month cells are 0/1 flags, so a worker's caseload for a month is a column
sum, not a value to read. `matrix: true` routes it to a bespoke reader.

It is also the only source of history in the export set, which finally gives
the dashboard a real trend line: **active cases ran 54 → 64 → 56 across 2026**.

### Where the numbers land

Loading all six reports together:

| | |
|---|---|
| Open cases | 52 |
| Workers | 43 |
| Distinct obligations | 2,766 (after removing 1,337 duplicates) |
| Overdue | 1,556 |
| — actionable (under a year) | **902** |
| — abandoned (over a year) | 654 |
| Due soon | 181 |

---

## All ten exports verified

Every report the dashboard depends on has now been run through
`inspect:export` against a real export. **10 of 10 resolve.** Four needed
schema work beyond an alias:

**`ontime` is not a monthly rollup.** Despite the "% On Time by Program"
label, the export is one row per completed item with its days-variance:
`Avg Days Var. | [year] | [worker] | [type] | Date | Name`, columns 1–3
unlabelled. That is better than a rollup — the percentage is derived as the
share of rows with variance ≤ 0, so it can be cut by month, worker or task
type. Over 3,184 completed items the agency runs **41.1% on time**, ranging
37–48% month to month, with mean lateness improving from +61 days in January
to +17 in August.

**`openbeds` carries more than beds.** Street `Address` and `Phone` for every
home, and an `Active Placements` column listing the children in each home **by
name, gender and age**. All three are declared sensitive.

**`staffexp`** is `Date | Title | Name` — the requirement is in `Title`.

**`caseload`** is the cross-tab described above.

### The free-text lesson

De-identifying these together surfaced a real defect. Free text was being
scrubbed against each file's *own* name columns, but a case note routinely
names someone who appears as a name column only in a *different* report — the
open-beds placements column lists children who are nowhere in that file's own
name columns. Those names survived. The synthetic mapping is now built once
across the whole run and shared, which is also why all reports must be
de-identified in a single invocation.

A backstop now also catches the "Ms. Surname" form that case notes use for
people who appear in no name column anywhere.

---

## Report inventory — what feeds what

The dashboard's five "spine" metrics all map to reports that already exist.

| Metric | Report | View code |
|---|---|---|
| Done | Activities Completed by Date | `V_ALLBYCOMPLETION_ACTIVITIES-C` |
| Pending | In Process by Date | `V_TASKS_INPROC-C` |
| Overdue | Due Soon / Past Due (case + home) | `V_TASKS_INPROC_PASTDUEBYDATE-C`, `V_HOMETASKS_INPROC_PASTDUEBYDATE-C` |
| Load | Monthly Census by Worker | `V_CASELOADS_WKR_MONTH-C` |
| On-time % | % On Time by Program | `V_MONTHVAR-C` |

Supporting context:

| Purpose | Report | View code |
|---|---|---|
| Open case roster | Foster Care Open Cases | `V_CLIENTS_LASTNAME_ACTIVE-C` |
| Capacity | Available Homes — Open Beds | `V_HOMES_AVAILABLE-C` |
| Court dates | Next Court Date | `V_CLIENTS_NEXTCOURT-C` |
| Medical due | Next Well Child Visit | `V_CLIENTS_NEXTMEDICAL-C` |
| Staff certifications | Events + Expirations by Date | `V_STAFF_EXPBYDATE-C` |
| Intake pipeline | Pending Referrals | `V_REFERRALSBYDATE-C` |
| Compliance trend | Non-Compliant by Program | `V_MONTHNC-C` |

---

## Data-quality caveats

**The `Worker` column means "entered by", not "assigned to."** Confirmed with
the agency. In an August sample of 145 completions across 41 children and 9
workers — the `V_ALLBYCOMPLETION_REPORTS-C` export, since verified — one person
logged 65 items, 45% of the total. That is a
**documentation-entry concentration** and a single point of failure in the
process; it is *not* evidence of workload imbalance, and must never be labelled
as caseload in the UI. True caseload comes only from `V_CASELOADS_WKR_MONTH-C`.

Revisit if the exec team later determines the column means something else.

**Header layout is irregular.** The sample export carried three unlabelled
leading columns (year, month, record type) before the real header row, and
grouping rows are interleaved with data rows. The loader locates the header by
scanning for known column names rather than assuming row 0, and skips rows where
every required field is blank.

---

## Also worth raising with the ExtendedReach admin

- **Administration → Export Data** is an admin-level bulk export that dumps
  whole tables — Cases, Case Activities, Case Reports, Placements, Homes, plus
  mailing lists — bypassing report filters entirely. It may replace several of
  the ten report exports with one action, and is worth testing. Also worth
  knowing who holds that permission, from a governance standpoint.
- **Administration → Import Data** lists templates named after other Texas
  child-placing agencies (DePelchin, Arms Wide, Forever Families, SJRC,
  TruLight127 and others). These are most likely generic templates shipped to
  all customers, but confirm with the vendor that they do not indicate a live
  data-exchange relationship.
- **Administration → Audit Log** is a full access/edit trail filterable by date,
  event type and user. Use it to evidence what the export account touched.

---

## Dependency note

`exceljs@4.4.0` pulls `uuid@8.3.2`, which carries advisory
[GHSA-w5hq-g745-h8pq](https://github.com/advisories/GHSA-w5hq-g745-h8pq)
(moderate). **The vulnerable path is not reachable here:** the advisory concerns
`uuid` v3/v5/v6 called with an explicit `buf` argument, and exceljs calls only
`uuidv4()` with no buffer (`lib/xlsx/xform/sheet/cf-ext/cf-rule-ext-xform.js`).

SheetJS (`xlsx`) was rejected as the alternative — its last npm release, 0.18.5,
carries unpatched prototype-pollution and ReDoS advisories that _are_ reachable
through parsing.

Re-check on upgrade rather than treating this note as permanent.

---

## The morning board, and two defects it surfaced

_2026-08-24. Building the four-tier morning triage board
(`docs/morning-board.md`) required reconciling the dashboard's displayed
figures against the numbers recorded above. They did not match, for two
reasons — both in the dashboard, not the exports._

### 1. The UI was showing roughly half the backlog it had loaded

`scopeDataset()` filtered obligations by whether their subject joined to the
52-row open-cases roster, and applied that filter to **every** role — including
an agency-wide scope, which has no permission narrowing to do. The effect was
that 1,627 of 2,766 obligations (59%) never reached the executive view:

| Population | Count | Why it does not join |
|---|---|---|
| Home-subject tasks | 371 | Belong to a home, not a child. No case exists. |
| Case tasks off the open roster | 1,256 | Client is not an *open* case — closed cases still carry open work. |

So the dashboard reported ~634 overdue where this document records 1,556. The
loader was right the whole time; the presentation layer discarded the
difference and gave no indication it had.

Permission filtering and join filtering are now separate concerns. Team and
personal scopes still narrow through the case join — an obligation that joins
to no case cannot be attributed to a worker, so it cannot be shown to one.
Agency-wide scopes no longer inherit that join as though it were a permission,
and the unattributable count is reported rather than silently absorbed.

### 2. `Scheduled` and `Event` rows were being aged into the backlog

`stateFor()` correctly treated the two calendar statuses as satisfied, but it
expressed that only as a `state` of "ok" — a value indistinguishable from
"settled work". Anything recomputing urgency from the due date, as a morning
board must, had no way to know those rows were never date-driven obligations,
and swept every past calendar entry into the overdue tiers.

The status judgement is now recorded as `calendarOnly` at load. Whether a row
is work that can be late is decided once, from its status; only *when* it is
due is recomputed later. This was caught by reconciliation, not by review — the
tiers were 14 items heavier than this document's figures, and the discrepancy
was the only reason to look.

### Reconciliation

With both fixed, and the date pinned to 2026-08-22 to match this audit, the
board reproduces every figure recorded above exactly:

| Measure | Recorded here | Board |
|---|---|---|
| Distinct obligations | 2,766 | 2,766 |
| Overdue | 1,556 | 1,556 |
| — actionable (under a year) | 902 | 902 |
| — abandoned (over a year) | 654 | 654 |
| Due soon | 181 | 181 |

### `needapproval_case` is now loaded

It is the only export naming the approver (`Submit To`), so the approval
queue's distribution — the finding that one person holds 51% of it — is
unreachable without it. It is deduplicated against the Submitted rows already
ingested from the task reports, keyed on subject + type; that key is coarser
than the subject + type + due date used elsewhere, because this report carries
no due date, and it is deliberately biased toward dropping a real row rather
than inventing one. The count lands in `diagnostics.approvalsDeduplicated`.

Verified against a synthetic export with the real headers: of 208 rows, 66
merged into obligations already present and **tiers 1, 3 and 4 did not move**.
Adding the approval queue does not inflate the backlog, which was the risk.

No `needapproval_case` file exists in `data/demo`, so the public demo shows
tier 2's count without its approver breakdown, and says so on the page rather
than rendering an empty chart.

---

## De-identification failure — the `type` column

_2026-08-24. Found while preparing the morning board for deployment. Recorded
here in full because the corrective action depends on understanding the shape
of the mistake, not just the instance._

### What happened

`npm run deidentify` scrubs the fields `schema.ts` declares sensitive. For the
task reports that was `client`/`home`/`worker` and `description`. **The `type`
column was declared as nothing and passed through untouched.**

In this agency's data that column is not structural vocabulary. Certification
and training items are named after the person they belong to:

```
SIDS Expires (<given>)
Valid Drivers License Expires (<given> <surname>)
Child Logs (<given>, <given>)              <- sibling groups
```

**55 distinct real given names across 170 rows of `pastdue_home`** survived
de-identification, reached `data/demo`, and were committed to a **public**
GitHub repository and served from a **public** Netlify demo with no password.
They are foster parents and household members; the sibling-pair form names
children.

### Why the existing safeguards missed it

Three separate things had to line up, and all three did.

1. **Sensitivity is declared per field, and nobody declares a `type` column.**
   It reads as an enum. In 6 of 10 reports it very nearly is.
2. **`scrubText`'s backstops did not match the shape.** It catches
   `Surname, Given` and `Ms. Surname` — the forms found in case notes. A bare
   given name in parentheses matches neither.
3. **The de-identifier's own output looked healthy.** It reports rows, people
   and cells replaced. Those counts were all correct. They describe what it
   scrubbed, and say nothing about what it never examined — which is precisely
   where the failure was.

The audit's earlier "free-text lesson" identified this class of bug: names
appear in fields not classified as name fields. It recurred anyway, in a
column that looked structural rather than free-form.

### The fix

- `type` declared as free text on all seven reports that carry one, including
  the three that previously had no `sensitivity` block at all.
- A parenthetical backstop in `scrubText`, holding back only recognisable task
  vocabulary. A false positive corrupts a demo label; a false negative
  publishes a child's name, so the bias is toward replacing.
- The generic `Surname, Given` backstop is now anchored to skip parentheticals,
  so a sibling pair stays a pair instead of being rewritten twice.
- `synthGiven()` for contexts holding a first name alone — substituting a full
  identity there would change the shape of the data as well as the name.
- `scripts/repair-demo-type-column.ts` repaired the 170 committed labels in
  place. The de-identifier could not be re-run: `buildPools` excludes every
  name found in its input, so a second pass over already-scrubbed files
  depletes the pool to nothing. That guard is correct; it just makes
  re-scrubbing impossible by design.
- **`npm run verify:deidentified`** — a fail-closed check over EVERY column of
  every file, masked output, non-zero exit on any finding. This is the control
  that was missing. The de-identifier verifies its own intentions; this
  verifies the artefact.

### Verified

| Check | Result |
|---|---|
| Canary names through the fixed scrubber | none survived, all three shapes |
| Task vocabulary preserved | `(Medication Review)`, `(Quarterly)`, `(Home)` intact |
| `verify:deidentified` over `data/demo` | PASS, 10 files |
| Audit figures after repair | 2,766 / 1,556 / 902 / 654 / 181 — all unchanged |

### Still outstanding

Fixing the data forward does not unpublish it. The names remain in the public
repository's **git history**, and GitHub keeps orphaned blobs reachable and
cached even after a force-push. Removing them properly means rewriting history
*and* asking GitHub Support to purge the cache — and assuming the data may
already have been fetched. **The repository is still public.** That decision,
and whether this needs to be reported to the agency under its breach
procedures, sit with the exec team.
