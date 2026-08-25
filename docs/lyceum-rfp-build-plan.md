# Lyceum RFP automation — build review and plan of record

**Reviewed:** 2026-08-24 · **Source:** Lyceum Group project brief (2026-08-24)

Contains no client, personnel, or licence data. The source brief carries real
names, PE licence numbers and TxDOT personnel record numbers; none of it is
reproduced here, per the brief's own standing guardrail.

---

## 1. The finding

The brief describes a **managed service** — Lyceum operates everything, the
operator does the work, the client receives a finished draft. The product as
described verbally is **self-serve** — firms sign up, build their own profile,
the system decides whether they qualify, then drafts for them.

These are different builds. Mechanical proof: the tenant wall in Make is a
hard-coded `firm_id` in module 1. One scenario equals one firm. That cannot
serve a second self-serve signup.

Against the brief, the build is ~40% complete. Against the self-serve product,
closer to 15%, and almost all the overlap is the Supabase schema.

| | Managed service | Self-serve |
|---|---|---|
| Enters firm data | Operator | The firm (needs intake UI) |
| Reviews the draft | Operator | Nobody, unless built |
| Tenant isolation | App-level survivable | DB-level mandatory day one |
| Make.com | Internal tool, acceptable | Customer runtime, wrong tool |
| Assembly | Correct fit | Cannot do custom intake/logic |
| Time to first dollar | 4–6 weeks | 3–4 months |
| Worst case | Operator catches it | Bad proposal under a sealed PE signature |

## 2. Path A — concierge first

Finish the managed service; sell to the firms already supported.

1. Week 1 — security truth-up: 2FA on, one-pager reworded to only true claims,
   seed contacts deleted, staff email domain fixed. Half a day; blocking
   because the one-pager is already circulating.
2. Weeks 2–3 — library assembly + drafting layer only.
3. Week 4 — five real pursuits end to end.
4. Week 5 — measure minutes of operator edit time per draft.

Gate: draft lands at <= 30 min edit time and one firm pays.
Cost: ~zero. Risk: delivery layer gets built twice.

## 3. Path B — product-grade foundation

1. Weeks 1–2 — real auth, `firm_id` claim in every session token, RLS actually
   evaluating, no master key reachable from a client request.
2. Weeks 3–5 — intake (precert report, staff roster, HUB certs, past
   performance). This is the product and is currently undesigned.
3. Weeks 6–8 — gate logic moved into Postgres.
4. Weeks 9–12 — assembly, drafting, document output.
5. Weeks 13–14 — two-firm pilot.

Gate: a firm completes a profile without calling. Cost: ~$25–50/mo + model
usage. Risk: three months before draft quality is known.

## 4. Recommendation

**Path A's business on Path B's foundation. Stop investing in Make.**

Cut backlog items 2 and 6 (clean Make account, rebuild Scenarios 01/02). That
pays migration cost to move onto a platform the brief already documents as a
dead end: no `and()`/`or()`/`not()`, team-scoped connections, webhook URLs that
break on every move. The prototype has done its job — it proved the gate logic
and surfaced the `18.2.1` / `8.2.1` collision.

Build library assembly and drafting as the first two endpoints of the real
application. Assembly is a query that already exists (`assemble_qualifications`).
Drafting is awkward in Make (page budgets, compression pass, retries) and
natural in code. Then operate it as a concierge service: sign-in exists but is
dark; flip it on when drafting quality is proven.

Backlog: 10 items -> 6. Items 2 and 6 cut. Item 5 (per-firm tokens) moves to
week one, free with real auth. Items 1, 3, 4, 7 stay, mostly clerical. Items
8, 9, 10 are the work.

## 5. Answers to the seven open questions

**Q1 — Make the right orchestrator?** No for anything customer-facing; fine as
personal automation. The boolean ceiling is already documented.

**Q2 — Does the JWT approach still hold?** Verified, with three corrections.
Custom claims still reach Postgres via `request.jwt.claims`, readable with
`auth.jwt()`.
- Minting is a **Custom Access Token Hook** (a Postgres function registered
  under Authentication -> Hooks). It must return the complete claims object
  including all required claims, not just `firm_id`. Returning only the custom
  claim fails sign-in for every user at once.
- Claims are frozen at issue time; a change applies on refresh (~1h). Harmless
  for `firm_id`; makes any future "switch firm" a forced re-login.
- The custom `lyceum_tenant` role works — PostgREST switches into the role named
  in the token — but is off the beaten path and most tooling assumes the standard
  role. Cheaper equivalent: keep the standard role, carry `firm_id` as a claim,
  rely on RLS with `FORCE`. Policies don't reference the role name, so nothing
  is lost.
- Not in the brief: legacy anon/service/JWT secrets **can no longer be rotated**.
  Migrate to asymmetric signing keys and the publishable/secret key pair.

**Q3 — master key in Make acceptable interim?** Not as it sits. The risk is the
combination: a non-rotatable credential, in a workspace shared with an unrelated
business, alongside a social connection authorized under a third party's name,
on an account with 2FA off. Acceptable briefly once 2FA is on and exactly one
real firm's data exists. Unacceptable at firm #2 — that key ignores every policy
unconditionally.

**Q4 — one-pager audit.**

| Claim | Verdict | Action |
|---|---|---|
| Point-in-time recovery | False | Buy the paid tier or delete the sentence |
| MFA enforced everywhere | False | Fix in infra today; free, ten minutes |
| Per-firm DB-level isolation | Aspirational | True once tokens carry `firm_id`; until then reword to application-level |
| "No employee error... can surface one firm's data to another" | Overstated absolute | Replace with what is actually done |
| Role-based access | True now | Keep |
| Contact address | Mismatch | Portal invite and letterhead must share a domain |

**Q5 — page budget enforcement.** Hard section caps derived from evaluation
weights, enforced as **character** budgets, verified by rendering. Not token
budgeting — tokens don't map to pages, the template does.
1. Subtract fixed parts (PM resume page, org table, appendices), measured
   empirically in the real template.
2. Split remaining characters by scoring weight (35/30/25/10 on a nine-page
   submission).
3. Generate each section independently against its own budget. Per-section
   budgets are hit; whole-document allocation is not.
4. Render and count pages. If over, ONE compression pass with the specific
   overage: "cut 340 characters, preserve every number, licence and proper
   noun." Never a vague "make it shorter" — that is where facts disappear.

**Q6 — subprovider intake.** Subs never onboard. Primes already collect sub
precert reports and HUB certificates during teaming. The prime uploads them;
store as staff/certification records inside the **prime's** tenant, tagged as a
teaming partner. Set matching doesn't care who employs the person. Add a
"last verified" date and surface staleness on any pursuit. Side benefit: every
sub that passes through is a warm introduction.

**Q7 — sequencing.** Prototype drafting first, with two non-negotiable
exceptions costing hours not weeks: 2FA on, one-pager made true. Ordering rule:
anything touching a real client's data waits for the foundation; anything
touching only synthetic data goes first.

## 6. Raised, not asked

- **The fillable forms are likely worth more than the AI layer.** Deterministic
  lookup, no model, no page budget, no invention — and the part of a submission
  where an error most reliably disqualifies. Decide with one number: hours per
  pursuit on narrative vs forms and tables.
- **A model workspace per client is over-engineering.** One workspace, one
  server-held key, one spend cap, per-firm request tagging for cost attribution.
  Seven workspaces means seven keys to rotate and zero isolation benefit — the
  server is the only caller and already knows which firm it serves.
- **Terminology.** The agency issues the RFP/RFQ; the firm responds with a
  proposal, SOQ or letter of interest. Firms do not "fill out an RFP." The brief
  gets this right; product copy must too.
- **Liability is unaddressed.** Three failure modes: a false GO burns forty
  hours; a false NO-GO loses a winnable contract and is never discovered; a
  generated narrative asserting an unheld certification is a false statement to
  a state agency on a sealed document. Mitigations: state that output is a draft
  for review by a licensed professional and the sealing engineer owns the
  content; confirm E&O coverage extends to software output before self-serve;
  store every gate decision immutably with inputs and as-of date
  (`eligibility_evaluations` already exists).
- **Two permanent regression tests, both from real documents:** the HUB
  certificate approved 2014 / expired 2017, and the `8.2.1` vs `18.2.1` pair.
- **Second date check:** certifications valid at submittal but expiring during
  the contract term. A warning, not a gate — but one a good consultant raises
  and an automated system otherwise drops silently.

## 7. Open questions for the operator

**Blocking:** managed service or self-serve? "Managed now, self-serve within a
year" is a fine answer but must be said out loud — if self-serve is anywhere in
the plan, no further hours go into Make.

Product shape
1. If self-serve, who reads a draft before it reaches the agency? If nobody, the
   quality gate and disclaimer must be built before launch.
2. Does the client receive an editable document or a submission-ready package?

Data intake
3. Where does firm precertification data come from today — firm-downloaded
   report, or operator lookup? PDF, spreadsheet, or on-screen?
4. Same for staff: is there a per-employee report carrying personnel record
   numbers, and who can pull it?
5. For the seven existing firms, is library material consolidated or scattered
   across old proposal PDFs? If scattered, month one is archaeology and needs
   pricing.

Volume and scope
6. Split between short constrained state submissions and long-form MPO packages.
7. Hours per pursuit on narrative vs forms/tables — decides whether the drafting
   layer or the forms layer is built first.
8. Is v1 state contracts only, or MPOs too?

Business
9. Pricing per pursuit or monthly — decides whether the go/no-go check is free
   (lead magnet) or paywalled.
10. Does existing E&O coverage extend to software output?
11. Is the senior domain contact a partner or a client contact? Changes portal
    requirements and access.

Incoming RFPs
12. Are the two incoming RFPs template models or a test set? Ideally one of
    each. A *winning* response to either is worth more than the solicitation:
    the solicitation gives the required shape, the winner shows what scored.

---

## Sources for the Supabase verification (Q2)

- https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook
- https://supabase.com/docs/guides/database/postgres/custom-claims-and-role-based-access-control-rbac
- https://supabase.com/docs/guides/auth/signing-keys
- https://supabase.com/docs/guides/database/postgres/roles
