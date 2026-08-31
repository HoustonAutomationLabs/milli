# Lyceum Group — home page

`index.html` is the home page that lives inside the Assembly portal. One self-contained
file: no build step, no framework, no bundler. Open it in a browser to preview it, or
paste it into Assembly as a custom page / embed.

## What to swap before it goes live

Everything that needs your input is marked `TODO(lyceum)` in the source. Search for that
string — there are five:

| Location | What to replace |
|---|---|
| Masthead CTA | "Start a working session" → your Assembly booking link or message channel |
| Hero, both buttons | Intake link, and the `#how` anchor if you'd rather deep-link |
| Closing band | Intake form URL |
| Closing band, email | `hello@lyceumgroup.com` → the real address **on your domain**, not a personal inbox |
| Footer links | Contact / privacy destinations |

**The logo.** The mark in the masthead is an SVG drawn in the spirit of your gold
logo — a column, a ring, a circuit node — because the PNG wasn't available to embed.
To use the real one, drop it at `lyceum/assets/lyceum-mark.png` and replace the
`<svg class="brand-mark">…</svg>` block with:

```html
<img src="assets/lyceum-mark.png" alt="" class="brand-mark" />
```

The transparent-background version works as-is on the dark ground. There's a comment at
that spot in the source saying the same thing.

## Claims policy

The numbers on the page are deliberately limited to things the project brief actually
establishes:

- **5–10 responses/week across seven firms** — the consulting work being productized.
- **70–80% library content** — measured against the El Paso LOI and the Tyler MPO RFQ.
- **7 checks** — the go/no-go gate as built.
- **0 AI in the eligibility decision** — a design commitment, and a real differentiator.

Deliberately **not** on the page: the `150× ROI`, `~$10 per proposal` and `40–80 hours
saved` figures from the earlier draft. No client is onboarded yet, so none of them can
be substantiated if a prospect asks — and the first person to ask will be an engineer.

Also deliberately absent: any security or compliance claim. Per §13 of the project
brief, several claims on the client-facing security one-pager are aspirational rather
than true today (MFA is off on the Make account, the Supabase free tier has no
point-in-time recovery, and no per-firm JWTs have been minted, so row-level security
isn't yet evaluating against real tenants). Add a security section here **after** the
infrastructure matches the wording, not before.

## Sample data

The Go/No-Go panel in the hero runs the synthetic `Demo Engineering LLC` payload from
§6 of the brief — 5 of 7 checks, `8.5.1` uncovered, self-performance 45% against a 55%
requirement. No real firm, engineer, PE license number or personnel record number
appears anywhere in this file, per the standing guardrail. Keep it that way: this page
is public-facing.
