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
groups (Muse, Wade, Garcia, Clark), so name-matching will eventually collide,
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
the backlog and shows staff as delinquent for work they completed. `stateFor()`
now treats Submitted as satisfied. Netting them out:

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
workers, one person logged 65 items — 45% of the total. That is a
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
