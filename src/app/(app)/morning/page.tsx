import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { can } from "@/lib/rbac";
import { recordAccess } from "@/lib/audit";
import { boundWorkerNames, resolveScope } from "@/lib/demo-roles";
import { getDataset } from "@/lib/zoho/client";
import { scopeDataset } from "@/lib/metrics";
import { TIER_ORDER, onTimeSummary, triageBoard, type Tier, type TieredItem } from "@/lib/triage";
import { ABANDONED_AFTER_DAYS } from "@/lib/aging";
import { Card, SectionTitle } from "@/components/ui";

export const metadata = { title: "Morning board" };

const TONE_COLOR: Record<Tier["meta"]["tone"], string> = {
  risk: "var(--risk)",
  warn: "var(--warn)",
  neutral: "var(--ink)",
  good: "var(--good)",
};

/**
 * "3 days" / "1.4 years" — an age a reader can weigh without doing division.
 *
 * The year boundary sits just past the tier-4 cutoff on purpose: at 365 days
 * exactly an item is still tier 1, and rendering that as "1.0 years" next to a
 * tier-4 item reading the same would make the two tiers look interchangeable.
 */
function humanAge(days: number): string {
  const d = Math.abs(days);
  if (d < 45) return `${d} day${d === 1 ? "" : "s"}`;
  if (d <= 365) return `${Math.round(d / 30)} months`;
  return `${(d / 365).toFixed(1)} years`;
}

function TierCard({ tier, rank }: { tier: Tier; rank: number }) {
  const { meta } = tier;
  return (
    <Card className="flex flex-col">
      <div className="flex items-baseline gap-2">
        <span className="text-[12px] font-semibold text-muted tnum">{rank}</span>
        <span className="text-[13px] font-medium text-muted">{meta.label}</span>
      </div>
      <div
        className="mt-2 text-3xl font-semibold tracking-tight tnum"
        style={{ color: tier.count === 0 ? "var(--good)" : TONE_COLOR[meta.tone] }}
      >
        {tier.count}
      </div>
      <div className="mt-1 text-[13px] font-medium" style={{ color: "var(--accent)" }}>
        {meta.owner} acts
      </div>
      <p className="mt-2 text-[13px] leading-snug text-ink-soft">{meta.rule}</p>
    </Card>
  );
}

function ItemRow({ entry, caseLabel }: { entry: TieredItem; caseLabel: string }) {
  const { item } = entry;
  const detail =
    entry.tier === "awaiting_approval"
      ? entry.waiting === undefined
        ? item.approver
          ? `with ${item.approver}`
          : "awaiting approval"
        : `waiting ${humanAge(entry.waiting)}${item.approver ? ` · ${item.approver}` : ""}`
      : entry.age > 0
        ? `${humanAge(entry.age)} overdue`
        : `due in ${humanAge(entry.age)}`;

  return (
    <li className="flex items-start justify-between gap-3 py-2">
      <div className="min-w-0">
        <div className="truncate text-[14px] font-medium text-ink">{item.label}</div>
        <div className="text-[13px] text-muted tnum">{caseLabel}</div>
      </div>
      <div className="shrink-0 text-right text-[13px] text-ink-soft tnum">{detail}</div>
    </li>
  );
}

/**
 * Says out loud that this demo account is standing in for real workers.
 *
 * Without it a viewer signed in as one of the sample accounts reasonably reads
 * the caseload on screen as belonging to the name in the sidebar. It does not.
 */
function DemoBindingNote({ names }: { names: string[] }) {
  return (
    <p className="mt-2 text-[13px] text-muted">
      Demo account &mdash; the sample sign-in has no caseload of its own in this
      export, so it is showing the work of{" "}
      <span className="text-ink-soft">{names.join(", ")}</span>.
    </p>
  );
}

export default async function MorningPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const data = await getDataset();
  const { scope, boundTo } = resolveScope(user, data);
  const scoped = scopeDataset(data, scope);
  const board = triageBoard(data, scoped, { limit: 6 });
  const onTime = onTimeSummary(data);

  recordAccess({ id: user.id, role: user.role }, "view_morning_board", {
    meta: { cases: scoped.cases.length, backlog: board.backlogTotal },
  });

  // Case ids only — never a child's name in a broad view.
  const caseLabel = new Map(scoped.cases.map((c) => [c.id, c.displayId]));

  // Worker names are not PHI, but who holds which queue is management
  // information rather than something a caseworker needs to do their own
  // morning. Same gate as the compliance register.
  const showHolders = can(user, "viewComplianceRegister");

  const approval = board.tiers.awaiting_approval;
  const topApprover = approval.holders[0];

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">Morning board</h1>
        <p className="mt-1 max-w-3xl text-[15px] text-ink-soft">
          The same work, sorted by who has to move next. Tiers 1, 3 and 4 divide
          the {board.backlogTotal} open obligation
          {board.backlogTotal === 1 ? "" : "s"} in your access between them, each
          counted once. Tier 2 is a separate queue and is not added in.
        </p>
        {boundTo?.length ? <DemoBindingNote names={boundWorkerNames(boundTo, data)} /> : null}
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {TIER_ORDER.map((id, i) => (
          <TierCard key={id} tier={board.tiers[id]} rank={i + 1} />
        ))}
      </section>

      {/* The finding that outlives the dashboard. Stated, not buried. */}
      <Card className="mt-6 border-l-4" style={{ borderLeftColor: "var(--accent)" }}>
        <SectionTitle>What the board does not fix</SectionTitle>
        <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-ink-soft">
          {onTime ? (
            <>
              Completion is running{" "}
              <strong className="font-semibold text-ink tnum">{onTime.pct}% on time</strong> across{" "}
              <span className="tnum">{onTime.sample.toLocaleString()}</span> completed items,{" "}
              {onTime.from} to {onTime.to}.
            </>
          ) : (
            <>On-time completion is not loaded from the current data source.</>
          )}{" "}
          Triage moves work between these four tiers; it does not change that
          rate. A backlog this size against that completion rate is a staffing
          and process question, and the four owners above are four different
          conversations — hiring caseworkers drains tiers 1 and 3, does nothing
          for tier 2, and nothing at all for tier 4.
        </p>
      </Card>

      {/* Tier 2's distribution is the whole point of separating it out. */}
      {showHolders && approval.count > 0 ? (
        <Card className="mt-6">
          <div className="mb-1 flex items-baseline justify-between gap-4">
            <SectionTitle>Who the approval queue is waiting on</SectionTitle>
            <span className="text-[13px] text-muted tnum">
              {approval.count} submission{approval.count === 1 ? "" : "s"}
              {board.approverUnknown
                ? ""
                : ` · ${approval.holders.length} approver${approval.holders.length === 1 ? "" : "s"}`}
            </span>
          </div>

          {board.approverUnknown ? (
            <p className="mt-3 text-[14px] text-ink-soft">
              The loaded exports show that this work is submitted, but not who it
              is queued with — no <code className="text-[13px]">needapproval_case</code>{" "}
              export is present. Add that report to the export set to see the
              distribution.
            </p>
          ) : (
            <>
              {topApprover && topApprover.share >= 0.3 ? (
                <p className="mt-3 text-[14px] text-ink-soft">
                  One approver holds{" "}
                  <strong className="font-semibold text-ink tnum">
                    {Math.round(topApprover.share * 100)}%
                  </strong>{" "}
                  of this queue. Adding caseworker capacity will not drain it.
                </p>
              ) : null}
              <ul className="mt-4 flex flex-col divide-y divide-line">
                {approval.holders.slice(0, 6).map((h) => (
                  <li key={h.name} className="flex items-center gap-3 py-2.5">
                    <span className="w-40 shrink-0 truncate text-[14px] text-ink">{h.name}</span>
                    <span className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                      <span
                        className="block h-full rounded-full"
                        style={{ width: `${Math.max(h.share * 100, 2)}%`, background: "var(--warn)" }}
                      />
                    </span>
                    <span className="w-20 shrink-0 text-right text-[13px] text-ink-soft tnum">
                      {h.count} · {Math.round(h.share * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      ) : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {TIER_ORDER.map((id) => {
          const tier = board.tiers[id];
          return (
            <Card key={id}>
              <div className="flex items-baseline justify-between gap-4">
                <SectionTitle>{tier.meta.label}</SectionTitle>
                <span className="text-[13px] text-muted tnum">
                  {tier.items.length < tier.count
                    ? `${tier.items.length} of ${tier.count}`
                    : tier.count}
                </span>
              </div>
              <ul className="mt-3 flex flex-col divide-y divide-line">
                {tier.items.map((entry) => (
                  <ItemRow
                    key={entry.item.id}
                    entry={entry}
                    caseLabel={caseLabel.get(entry.item.caseId) ?? entry.item.caseId}
                  />
                ))}
                {tier.count === 0 ? (
                  <li className="py-2 text-[14px] text-muted">Nothing in this tier.</li>
                ) : null}
              </ul>
            </Card>
          );
        })}
      </div>

      {/* Counting caveats belong on the page, not only in the docs. */}
      <Card className="mt-6">
        <SectionTitle>How these numbers are counted</SectionTitle>
        <ul className="mt-3 flex flex-col gap-2 text-[14px] leading-relaxed text-ink-soft">
          <li>
            Submitted work is never counted as caseworker backlog. It sits in
            tier 2 because the caseworker has finished it.
          </li>
          <li>
            <span className="tnum">{board.overlapWithBacklog}</span> submission
            {board.overlapWithBacklog === 1 ? " is" : "s are"} also past their due
            date. They are late, but not the caseworker&rsquo;s to finish, so they
            appear in tier 2 only.
          </li>
          {onTime ? (
            <li>
              The on-time figure is weighted across every month in the export,
              not read off the latest one. {onTime.to} on its own is{" "}
              <span className="tnum">{onTime.latestPct}%</span> over{" "}
              <span className="tnum">{onTime.latestSample}</span> items &mdash; the
              smallest sample in the series, because the export is taken
              mid-month. Treat a single month as noise.
            </li>
          ) : null}
          <li>
            Tier 4 is everything more than{" "}
            <span className="tnum">{ABANDONED_AFTER_DAYS}</span> days overdue. The
            cutoff is a setting, not a fact about the work &mdash; confirm it before
            it drives a write-off.
          </li>
          {scoped.unattributed > 0 ? (
            <li>
              <span className="tnum">{scoped.unattributed}</span> of these belong
              to no case on the open-cases roster &mdash; obligations on homes
              rather than children, and work still open on closed cases. They are
              counted in the tier totals but cannot be attributed to a caseworker,
              which is why the queue breakdowns cover fewer items than the tiers do.
            </li>
          ) : null}
          {board.undated > 0 ? (
            <li>
              <span className="tnum">{board.undated}</span> obligation
              {board.undated === 1 ? " carries" : "s carry"} no due date and sit in
              no tier. Giving them one would put work in front of a caseworker on a
              date the source system never set.
            </li>
          ) : null}
        </ul>
      </Card>
    </div>
  );
}
