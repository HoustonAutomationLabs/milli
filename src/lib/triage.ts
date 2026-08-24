/**
 * Four-tier morning triage.
 *
 * The dashboard's headline problem is 1,556 overdue obligations against 41%
 * on-time completion. Presented as one number that is only demoralising — it
 * says the agency is behind without saying who can do anything about it. The
 * morning board splits the same work by **who has to move next**:
 *
 *   1. Act today          — overdue, live, and the caseworker's to finish.
 *   2. Waiting on approval — done, submitted, sitting with a supervisor.
 *   3. Due soon           — not yet late; the only tier that is preventable.
 *   4. Needs a decision   — overdue past the abandonment cutoff; an exec has
 *                           to write these off or fund clearing them.
 *
 * The split matters because the fixes differ. Hiring caseworkers drains tier
 * 1 and 3. It does nothing for tier 2, which is queued behind 18 approvers,
 * one of whom holds 51% of it. And nothing drains tier 4 except a decision.
 *
 * Counting rules
 * --------------
 * Tiers 1, 3 and 4 **partition** the obligation backlog: every obligation the
 * loader produced lands in exactly one of them, or in none (settled work).
 * They never overlap, so they can be added up.
 *
 * Tier 2 is a different population and is deliberately NOT summed with the
 * others. It is drawn from the approval queue, which overlaps the backlog —
 * an item can be both past due and awaiting approval. Those items are held
 * out of tier 1 (`state` is "ok" for anything submitted, by design) so they
 * are never counted as caseworker backlog, but the reverse is not a
 * subtraction either. `overlapWithBacklog` reports the intersection instead
 * of hiding it.
 */

import { ABANDONED_AFTER_DAYS, DUE_SOON_DAYS, daysOverdue } from "./aging";
import type { ScopedCases } from "./metrics";
import type { CaseworkDataset, ComplianceItem } from "./zoho/types";

export type TierId = "act_today" | "awaiting_approval" | "due_soon" | "needs_decision";

export const TIER_ORDER: TierId[] = [
  "act_today",
  "awaiting_approval",
  "due_soon",
  "needs_decision",
];

export interface TierMeta {
  id: TierId;
  /** Short label for the tier card. */
  label: string;
  /** Who has to move next. This is the organising idea of the whole board. */
  owner: string;
  /** One line explaining exactly what qualifies, in the reader's terms. */
  rule: string;
  tone: "risk" | "warn" | "neutral" | "good";
}

export const TIERS: Record<TierId, TierMeta> = {
  act_today: {
    id: "act_today",
    label: "Act today",
    owner: "Caseworker",
    rule: `Past due, still open, and under ${ABANDONED_AFTER_DAYS} days old.`,
    tone: "risk",
  },
  awaiting_approval: {
    id: "awaiting_approval",
    label: "Waiting on approval",
    owner: "Supervisor",
    rule: "Finished and submitted. The caseworker has nothing left to do.",
    tone: "warn",
  },
  due_soon: {
    id: "due_soon",
    label: "Due soon",
    owner: "Caseworker",
    rule: `Not yet late. Falls due within ${DUE_SOON_DAYS} days.`,
    tone: "neutral",
  },
  needs_decision: {
    id: "needs_decision",
    label: "Needs a decision",
    owner: "Executive",
    rule: `Overdue by more than ${ABANDONED_AFTER_DAYS} days. Clear it or write it off.`,
    tone: "neutral",
  },
};

/** One obligation, placed in a tier, with the age that put it there. */
export interface TieredItem {
  item: ComplianceItem;
  tier: TierId;
  /** Days past due. Negative for tier 3 (still upcoming). */
  age: number;
  /** Days the submission has been waiting. Tier 2 only. */
  waiting?: number;
}

/** Who is holding a tier, and how concentrated that holding is. */
export interface Holder {
  name: string;
  count: number;
  /** Share of the tier this one person holds, 0..1. */
  share: number;
}

export interface Tier {
  meta: TierMeta;
  count: number;
  items: TieredItem[];
  /** Largest holders first. Shares are over `attributed`, not `count`. */
  holders: Holder[];
  /** Items whose holder is known. `holders` sums to this. */
  attributed: number;
  /** Items no report attributes to anyone. Reported, never bucketed. */
  unattributed: number;
}

export interface TriageBoard {
  tiers: Record<TierId, Tier>;
  /** Tiers 1 + 3 + 4 — the obligation backlog, counted once. */
  backlogTotal: number;
  /**
   * Obligations that are BOTH past due and awaiting approval. Reported rather
   * than netted out: they are not caseworker backlog, but they are still late.
   */
  overlapWithBacklog: number;
  /** Obligations with no due date, which cannot be aged into a tier. */
  undated: number;
  /** True when no report in the set carried an approver column. */
  approverUnknown: boolean;
}

/**
 * Who holds an item, by tier, or null when nothing in the data says.
 *
 * Tier 2 is held by the approver named on the submission. Every other tier is
 * held by the **case's assigned caseworker**, resolved through the open-cases
 * roster — never by the task report's own `Worker` column, which records who
 * *entered* an item rather than who carries it. The audit is explicit that
 * labelling that column as caseload is wrong: one person logged 45% of an
 * August sample, which is documentation-entry concentration, not workload.
 *
 * Returning null rather than an "Unassigned" bucket is deliberate. Home-subject
 * tasks belong to a home rather than a child, and case tasks on closed cases
 * join to no open roster row; agency-wide that is well over half the set. Named
 * as a holder it would top every ranking and read as one person's queue.
 */
function holderOf(t: TieredItem, caseWorkerName: Map<string, string>): string | null {
  const raw =
    t.tier === "awaiting_approval"
      ? (t.item.approver ?? t.item.performedBy)
      : caseWorkerName.get(t.item.caseId);
  const clean = (raw ?? "").trim();
  return clean || null;
}

/**
 * Rank holders of a tier.
 *
 * Shares are computed over the *attributable* items only, so "holds 51% of the
 * approval queue" means 51% of the submissions whose approver is known — not a
 * percentage quietly diluted by rows that name nobody. The unattributable
 * count is returned alongside rather than folded in.
 */
function rank(
  items: TieredItem[],
  caseWorkerName: Map<string, string>,
): { holders: Holder[]; attributed: number; unattributed: number } {
  const by = new Map<string, number>();
  let unattributed = 0;
  for (const t of items) {
    const who = holderOf(t, caseWorkerName);
    if (!who) {
      unattributed++;
      continue;
    }
    by.set(who, (by.get(who) ?? 0) + 1);
  }
  const attributed = items.length - unattributed;
  const denom = attributed || 1;
  return {
    holders: [...by.entries()]
      .map(([name, count]) => ({ name, count, share: count / denom }))
      .sort((a, b) => b.count - a.count),
    attributed,
    unattributed,
  };
}

export interface TriageOptions {
  /** Overridable so the board is testable against a fixed date. */
  today?: Date;
  /** Items listed per tier. The counts are always the full figure. */
  limit?: number;
}

/**
 * Sort a scoped dataset into the four tiers.
 *
 * Takes the output of `scopeDataset`, so a caseworker's board is built from
 * their records only — the scoping has already happened and this layer never
 * widens it. `data` supplies caseworker names for holder attribution and is
 * read for nothing else.
 */
export function triageBoard(
  data: CaseworkDataset,
  scoped: ScopedCases,
  opts: TriageOptions = {},
): TriageBoard {
  const today = opts.today ?? new Date();
  const limit = opts.limit ?? 8;

  // caseId -> assigned caseworker's name, for holder attribution.
  const workerName = new Map(data.caseworkers.map((w) => [w.id, w.name]));
  const caseWorkerName = new Map(
    scoped.cases.map((c) => [c.id, workerName.get(c.caseworkerId) ?? c.caseworkerId]),
  );

  const buckets: Record<TierId, TieredItem[]> = {
    act_today: [],
    awaiting_approval: [],
    due_soon: [],
    needs_decision: [],
  };

  let overlapWithBacklog = 0;
  let undated = 0;
  let sawApprover = false;

  for (const item of scoped.compliance) {
    // A scheduled visit or calendar event carries a date but is not an
    // obligation that can be late. Whether a row is date-driven work was
    // decided from its status at load time; re-deriving it here from the date
    // alone would sweep every past calendar entry into the backlog.
    if (item.calendarOnly) continue;

    const age = item.dueDate ? daysOverdue(item.dueDate, today) : null;

    if (item.awaitingApproval) {
      if (item.approver) sawApprover = true;
      // Late *and* blocked. Counted in tier 2 only, but the fact that it is
      // also past its due date is the agency's most under-reported number.
      if (age !== null && age > 0) overlapWithBacklog++;
      buckets.awaiting_approval.push({
        item,
        tier: "awaiting_approval",
        age: age ?? 0,
        waiting: item.submittedOn ? daysOverdue(item.submittedOn, today) : undefined,
      });
      continue;
    }

    if (age === null) {
      // No due date means no tier. Inventing one would put an obligation in
      // front of a caseworker on a date the source system never asserted.
      undated++;
      continue;
    }

    if (age > ABANDONED_AFTER_DAYS) {
      buckets.needs_decision.push({ item, tier: "needs_decision", age });
    } else if (age > 0) {
      buckets.act_today.push({ item, tier: "act_today", age });
    } else if (age > -DUE_SOON_DAYS) {
      buckets.due_soon.push({ item, tier: "due_soon", age });
    }
    // Anything further out is not this morning's problem.
  }

  // Oldest first everywhere: in tiers 1 and 4 that is the most overdue, in
  // tier 2 the longest-waiting submission, in tier 3 the soonest deadline.
  for (const id of TIER_ORDER) {
    buckets[id].sort((a, b) =>
      id === "awaiting_approval" ? (b.waiting ?? 0) - (a.waiting ?? 0) : b.age - a.age,
    );
  }

  const tiers = Object.fromEntries(
    TIER_ORDER.map((id) => [
      id,
      {
        meta: TIERS[id],
        count: buckets[id].length,
        items: buckets[id].slice(0, limit),
        ...rank(buckets[id], caseWorkerName),
      } satisfies Tier,
    ]),
  ) as Record<TierId, Tier>;

  return {
    tiers,
    backlogTotal:
      tiers.act_today.count + tiers.due_soon.count + tiers.needs_decision.count,
    overlapWithBacklog,
    undated,
    approverUnknown: buckets.awaiting_approval.length > 0 && !sawApprover,
  };
}

/**
 * The agency's most recent on-time completion rate.
 *
 * The board deliberately carries this: the four tiers describe a backlog, but
 * the reason the backlog exists is that only ~41% of work is finished on
 * time. Triage moves items between tiers; it does not change that rate.
 */
export function latestOnTime(data: CaseworkDataset): { pct: number; sample: number } | null {
  const last = data.onTime?.at(-1);
  if (!last) return null;
  return { pct: last.onTimePct, sample: last.sample };
}
