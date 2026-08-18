# Decision & Strategy — Casework Dashboard

**Prepared for:** Agency leadership (CEO, managers, staff) and stakeholders
**Status:** Draft for stakeholder decision

A shareable, formatted version of this brief is also available as a hosted page (ask the engagement
team for the link). This is the version of record that travels with the codebase.

---

## 1. Context — what we're solving

The agency runs its foster-care casework in **ExtendedReach** (a hosted case-management system for
child-placing agencies). Leadership wants a **modern, high-end dashboard** serving three audiences:

- **CEO** — agency-wide KPIs, compliance/risk posture, trends.
- **Managers** — team/caseload oversight, deadlines, exceptions.
- **Staff** — their own caseload, tasks, and upcoming due dates.

The goal is to **streamline how people see and act on data that already lives in ExtendedReach** —
not to re-key work. Two constraints frame every option:

1. **Data access is effectively Zoho Analytics-only.** The practical way to get case data out of
   ExtendedReach is its Zoho Analytics ("SOHO Analytics") path, which requires the agency to
   **upgrade its ExtendedReach plan**. This is the biggest assumption and must be validated first.
2. **This is regulated data.** Foster-care records include PHI, so the solution must be
   **HIPAA-aware** and meet **Texas DFPS** child-welfare data-handling rules.

## 2. Legal note (read first)

- ✅ **Legitimate:** building the agency's *own* system that is *functionally similar* to ExtendedReach.
- ❌ **High risk:** copying ExtendedReach's actual software — code, screen layouts, database schema,
  or branding. "The customer owns the copy" does not remove copyright/IP or terms-of-service exposure.

Every option below is scoped as **independent, original work**, never a clone.

## 3. The options

### Option A — Custom dashboard on top of ExtendedReach (via Zoho Analytics) ⭐ Recommended
Keep ExtendedReach as the system of record. Build a new, modern, role-based dashboard that reads data
through Zoho Analytics for CEO / manager / staff.
- **Cost:** ExtendedReach plan upgrade + our build/hosting. **Effort:** weeks. **Risk:** low —
  no migration, we never become the system of record. **Ownership:** agency owns the dashboard.

### Option B — Independent system the agency owns
Build a standalone, functionally-similar app the agency owns and eventually uses instead of ER.
- **Cost:** large build + ownership; still likely needs Zoho to migrate history. **Effort:**
  quarters. **Risk:** high — full HIPAA + DFPS liability, migration, change-management. **Ownership:**
  full, but inherits all responsibility ER carries today.

### Option C — Native Zoho Analytics dashboards only
Configure Zoho's own dashboards. Cheapest and fastest, but not the "high-end custom" product wanted;
limited UX/role control; locked into Zoho. Useful as an interim/fallback.

| | A: Dashboard on ER ⭐ | B: Own system | C: Native Zoho |
|---|---|---|---|
| Cost to agency | Plan upgrade + our build | Large build + ownership | Lowest |
| Time to value | Weeks | Quarters | Days |
| Compliance liability | Stays mostly with ER | Fully on the agency | Stays with ER/Zoho |
| Custom high-end UX | Full | Full | Limited |
| Data migration needed | No | Yes | No |
| Recurring ER cost | Yes | Eventually no | Yes |

## 4. Recommendation

**Pursue Option A now, architected so it can grow toward Option B later (phased).** Because the only
data tap is Zoho Analytics, even Option B would lean on Zoho to extract history — so Option A delivers
value from the same investment far faster and at much lower risk. Leadership's real need is
visibility and streamlining, which is a presentation problem, not a reason to replace the system of
record. Building Option A cleanly means Option B later becomes an extension, not a restart.

**Phasing:**
- **Phase 0 — Validate & scope:** confirm the ER→Zoho feed, catalog fields/reports, settle hosting/BAA.
- **Phase 1 — Build the dashboard:** role-based dashboard reading from Zoho, HIPAA-aware hosting,
  audit logging. *(This repository is the Phase 1 scaffold.)*
- **Phase 2 (optional):** deepen ownership only if the agency decides to move off ExtendedReach.

## 5. Recommended architecture (Phase 1)

- **Front end:** Next.js + TypeScript + Tailwind, hand-built components for a high-end feel.
- **Auth & roles:** CEO / Manager / Staff with least-privilege scoping, via a BAA-capable IdP.
- **Data layer:** server-side integration pulling from Zoho Analytics' REST/Data API, minimizing PHI
  at rest (query-through or short-lived encrypted cache, not a full copy).
- **Hosting:** HIPAA-eligible cloud under a signed BAA. (Vercel default is not HIPAA-covered.)
- **Cross-cutting:** encryption in transit + at rest, audit logging of PHI access, session controls.

See the repository `README.md` for how the scaffold implements this.

## 6. Compliance to design around

- **HIPAA:** signed BAA with the host and every subprocessor touching PHI (Zoho included); access
  controls, audit logs, encryption, breach procedures, minimum-necessary access per role.
- **Texas DFPS / foster care:** state confidentiality and data-handling rules in addition to HIPAA.
- **Principle:** the less PHI we store, the smaller the compliance surface.

## 7. Open decisions (Phase 0)

1. **ER → Zoho Analytics feed (critical):** existence, required plan upgrade, cost, refresh cadence,
   exposed fields/reports. Answer before further build commitment.
2. **Hosting & BAA ownership:** we-host vs. customer-hosts. Deliberately deferred.
3. **Does PHI need to leave Zoho at all,** or can sensitive fields stay masked/aggregated?
4. **Role definitions:** exact data each of CEO / manager / staff may see.
5. **Texas-specific rules:** which DFPS requirements the agency is held to.
