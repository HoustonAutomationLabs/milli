import type { ComplianceState } from "@/lib/zoho/types";

export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl border border-line bg-surface p-5 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-muted">{children}</h2>
  );
}

const STATE_STYLE: Record<ComplianceState, { bg: string; fg: string; label: string }> = {
  ok: { bg: "var(--good-bg)", fg: "var(--good)", label: "On track" },
  due_soon: { bg: "var(--warn-bg)", fg: "var(--warn)", label: "Due soon" },
  overdue: { bg: "var(--risk-bg)", fg: "var(--risk)", label: "Overdue" },
};

export function ComplianceBadge({ state }: { state: ComplianceState }) {
  const s = STATE_STYLE[state];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-semibold"
      style={{ background: s.bg, color: s.fg }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.fg }} aria-hidden />
      {s.label}
    </span>
  );
}

export function KpiCard({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "good" | "warn" | "risk";
}) {
  const toneColor =
    tone === "good"
      ? "var(--good)"
      : tone === "warn"
        ? "var(--warn)"
        : tone === "risk"
          ? "var(--risk)"
          : "var(--ink)";
  return (
    <Card>
      <div className="text-[13px] font-medium text-muted">{label}</div>
      <div className="mt-2 text-3xl font-semibold tracking-tight tnum" style={{ color: toneColor }}>
        {value}
      </div>
      {hint ? <div className="mt-1 text-[13px] text-ink-soft">{hint}</div> : null}
    </Card>
  );
}
