import type { TrendPoint } from "@/lib/zoho/types";

/**
 * Compact area+line trend of active cases. Pure inline SVG (no chart lib),
 * themed via CSS tokens, with a faint baseline grid and an emphasized endpoint.
 */
export function TrendChart({ data }: { data: TrendPoint[] }) {
  if (data.length === 0) return null;

  const w = 640;
  const h = 180;
  const padX = 8;
  const padY = 16;
  const values = data.map((d) => d.activeCases);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1, max - min);

  const x = (i: number) => padX + (i * (w - padX * 2)) / Math.max(1, data.length - 1);
  const y = (v: number) => padY + (1 - (v - min) / span) * (h - padY * 2);

  const line = data.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(d.activeCases).toFixed(1)}`).join(" ");
  const area = `${line} L${x(data.length - 1).toFixed(1)},${h - padY} L${x(0).toFixed(1)},${h - padY} Z`;
  const last = data[data.length - 1];

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        width="100%"
        height={h}
        role="img"
        aria-label={`Active cases trend, ${data[0].month} to ${last.month}, ending at ${last.activeCases}`}
        preserveAspectRatio="none"
        style={{ minWidth: 420 }}
      >
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((g) => (
          <line
            key={g}
            x1={padX}
            x2={w - padX}
            y1={padY + g * (h - padY * 2)}
            y2={padY + g * (h - padY * 2)}
            stroke="var(--line)"
            strokeWidth="1"
          />
        ))}
        <path d={area} fill="url(#areaFill)" />
        <path d={line} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinejoin="round" />
        <circle cx={x(data.length - 1)} cy={y(last.activeCases)} r="4.5" fill="var(--accent)" />
      </svg>
    </div>
  );
}
