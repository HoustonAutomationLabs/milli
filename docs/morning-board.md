# The four-tier morning board

_Design record for `/morning` — what the four tiers are, why the work is cut
this way, and which numbers are not allowed to be added together._

## Why not one number

The agency's position is 1,556 overdue obligations against 41.1% on-time
completion. As a single headline that figure is only demoralising: it says the
agency is behind without saying who can do anything about it, and it invites
the one response that does not work — telling caseworkers to catch up.

The board cuts the same work by **who has to move next**. Nothing is
recalculated to be kinder; the tiers sum to the same backlog. What changes is
that four different problems stop being reported as one.

| Tier | Who acts | What qualifies |
|---|---|---|
| 1. Act today | Caseworker | Past due, still open, under the abandonment cutoff |
| 2. Waiting on approval | Supervisor | Finished and submitted; the caseworker is done |
| 3. Due soon | Caseworker | Not yet late, due within 30 days |
| 4. Needs a decision | Executive | Overdue by more than the cutoff |

The fixes differ, which is the entire point. Hiring caseworkers drains tiers 1
and 3. It does nothing for tier 2, which is queued behind 18 approvers, one
holding 51% of it. Nothing drains tier 4 except an executive deciding whether
those records are still real work.

## Counting rules

**Tiers 1, 3 and 4 partition the backlog.** Every obligation lands in exactly
one of them or in none. They never overlap and may be added up. This is
enforced in `triageBoard()` and checked by the reconciliation below.

**Tier 2 is a different population and is never summed with the others.** It is
the approval queue, which overlaps the backlog: an item can be both past due
and awaiting approval. Those items are held out of tier 1 — `state` stays "ok"
for anything submitted, by design — so they are never counted as caseworker
backlog. The intersection is reported as `overlapWithBacklog` rather than
quietly netted out.

**Submitted is not overdue.** 165 of 997 past-due case tasks are finished work
sitting with a supervisor. Counting them as caseworker backlog overstates it
and shows staff as delinquent for work they completed.

**Scheduled and Event rows are not obligations.** They carry dates but cannot
be late. Whether a row is date-driven work is decided from its status once at
load (`calendarOnly`); only *when* it is due is recomputed at render. Deriving
it from the date alone swept every past calendar entry into the backlog — this
was a real defect, caught by reconciling against the audit's figures.

**The tier-4 cutoff is a setting, not a fact.** `ER_ABANDONED_AFTER_DAYS`
defaults to 365. It must be confirmed with the exec team before it drives a
write-off, and the board says so on the page.

## Attribution

Tier 2 is held by the **approver** named on the submission (`Submit To`).
Tiers 1, 3 and 4 are held by the **case's assigned caseworker**, resolved
through the open-cases roster.

Never by the task reports' own `Worker` column. That column records who
*entered* an item, not who carries it — one person logged 45% of an August
sample, which is documentation-entry concentration, not workload.

Items that name nobody are counted in the tier totals but excluded from the
holder ranking, and the excluded count is shown. Agency-wide that is 1,627 of
2,766 obligations: 371 home-subject tasks, which belong to a home rather than a
child, plus 1,256 case tasks whose client is not on the *open*-cases roster.
Folding them into an "Unassigned" bucket would top every ranking and read as
one person's queue; hiding them would make the shares wrong.

## The scoping defect this surfaced

`scopeDataset()` filtered obligations by whether their subject joined to the
52-row open-cases roster — for **every** role, including an agency-wide scope
that has no permission filter to apply. That silently withheld those same 1,627
obligations from the executive view, so the dashboard reported roughly half the
backlog the loader had just measured.

Permission filtering and join filtering are now separate. A team or personal
scope still narrows to cases the user may read and then to those cases'
obligations, because an obligation that joins to no case cannot be shown to
either without guessing whose it is. An agency-wide scope no longer inherits
the join as though it were a permission.

## Reconciliation

Run against the de-identified demo exports with the date pinned to 2026-08-22,
the day the audit was taken, every documented figure reproduces exactly:

| Measure | Audit | Board |
|---|---|---|
| Distinct obligations | 2,766 | 2,766 |
| Overdue (tier 1 + tier 4) | 1,556 | 1,556 |
| — actionable → tier 1 | 902 | 902 |
| — abandoned → tier 4 | 654 | 654 |
| Due soon → tier 3 | 181 | 181 |

Unpinned, the figures move with the calendar, which is the point of a morning
board.

## What it does not do

It does not change the 41.1% on-time rate. Triage moves work between tiers;
the reason the backlog exists is that fewer than half of all obligations are
finished on time, and that is a staffing and process question. The board states
the figure on the page rather than burying it, because the tool making the
problem visible is not the same as the tool fixing it.
