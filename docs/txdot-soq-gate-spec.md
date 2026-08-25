# TxDOT SOQ gate — specification derived from two PEPS solicitations

**Sources:** 601CT0000003362 (CEI, IH 35 McLennan Co., specific deliverable,
federal, DBE 12%, posted 2018-04-20) and 601CT0000003400 (ITS planning,
statewide, indefinite deliverable, streamlined, state, HUB 23.7%, posted
2018-05-30).

**Status:** derived from the RFQ cover documents only. The five attachment
templates (Q&R, PTC, SOQ Cover Page, NLC, HSP) have not been seen. Both
solicitations are from 2018 and must be diffed against a currently advertised
PEPS solicitation before any value here is hard-coded.

No firm or personnel data. TxDOT staff names and contact details from the
source documents are deliberately omitted.

---

## 1. Headline finding

**At the SOQ stage there is no narrative document.** Both documents state:
responses must be on the Q&R Template, "no other format will be accepted";
content outside the allotted space "will not be evaluated"; additional pages
will not be accepted. The submittal "must consist of and is limited to" five
attachments, all fillable TxDOT forms:

1. SOQ Cover Page
2. Questions & Responses (Q&R) Template
3. Project Team Composition (PTC) form, parts 1-3
4. Subprovider Contact Information (3362) **or** HUB Subcontracting Plan (3400)
5. Non-Listed Categories (NLC) Template

The nine-page narrative in the project brief belongs to the **short-list
stage**, not the SOQ stage — and 3400 has no written proposal at short list at
all, only an interview. Drafting is downstream of the gate, and for streamlined
solicitations it never occurs.

## 2. What varies between the two

| | 3362 | 3400 |
|---|---|---|
| Contract type | Specific deliverable, federal | Indefinite deliverable, streamlined, state |
| Goal program | DBE 12%, evidenced on PTC | HUB 23.7%, evidenced on signed HSP |
| Admin qualification | Required by SOQ deadline (or safe harbor) | Not required to compete |
| Preclusion | Declared; includes subsidiaries and affiliates | Not declared |
| Categories | 9 standard (68%) + 4 NLC (32%) | 6 standard (96%) + 1 NLC (4%) |
| Short list | Written proposal + interview (RFP/ICG) | Interview only (ICG) |
| Awards | 1 contract | 3 contracts, ~$5M each |
| Posting period | 21 days | 14 days |

Constant across both: 30% minimum prime self-performance; PM must be TX PE,
precertified in >=1 standard category, and employed by the prime; task leaders
precertified per category; everything evaluated **as of the SOQ deadline**; no
joint ventures; scoring 90% Q&R / 10% past performance.

**Correction to the brief:** the 35/30/25/10 weighting the template model
derives page budgets from appears in neither document. Both are 90/10.

**Past performance (10%) is not influenceable at bid time.** Read from TxDOT's
provider evaluation database. Absent scores default to the 5-year average
(147.48/150 = 98.2% of available points), so a firm with no history is barely
penalised and a firm with a poor history is worse off than a newcomer. The PM's
score follows the PM regardless of employer — past performance is an attribute
of a person, not only a firm.

## 3. The gate — 33 checks in five tiers

Current implementation scores 7 checks and returns a single GO/NO-GO. These
fail in materially different ways and must not be collapsed into one number.

### Tier 0 — non-responsive, rejected unread (12)

> **REVISED 2026-08-25.** The paper/USB mechanics below are obsolete. TxDOT
> moved procurement to an electronic portal; anything advertised after
> 2020-12-15 is submitted through it. Tiers 1-4 are unaffected — they derive
> from statute and administrative code, not delivery logistics.

| # | Check |
|---|---|
| 0.1 | Submitted before the deadline, to the minute. A submission is not made until **finalised** in the portal — uploaded files in a draft are not a response |
| 0.2 | Every requested-information upload slot filled (the electronic form of a missing attachment). Slots are set per solicitation |
| 0.3 | File types, sizes and counts within portal limits — verify per solicitation |
| 0.4 | ~~Paper bound with clip, no staples~~ **superseded** |
| 0.5 | ~~USB labelled with firm name and solicitation number~~ **superseded** |
| 0.6 | File naming convention — **verify**. 2018 rule was `<first 15 chars of legal name>_<last 6 digits>_Complete.pdf`; portals commonly keep a naming rule but TxDOT's current one must be read from a live solicitation |
| 0.7 | Only the listed attachments, in numerical order |
| 0.8 | Cover page complete including PM signature (explicit in 3400) |
| 0.9 | HSP present, current version, signed (state solicitations) |
| 0.10 | HSP developed in good faith — documented written notice to >=3 actively certified HUBs and to minority/women trade organisations, >=7 working days before submission, each carrying scope, plans location, bonding/insurance, qualifications, contact method |
| 0.11 | Every answer fits its allotted space (overflow is not rejected — it is not read) |
| 0.12 | Not a joint venture or joint response |

### Tier 1 — firm eligibility, as of the SOQ deadline (8)

| # | Check |
|---|---|
| 1.1 | Prime registered/licensed with TX Board of Professional Engineers, active |
| 1.2 | Prime and all subs registered with TX Secretary of State under the exact legal name used on the cover page and PTC; must match Comptroller registration and the TxDOT CCIS database; dba must be noted |
| 1.3 | Firm precert Active status (annual renewal 1 Jan - 31 Mar). Required for prime and any sub leading a standard category. **Not** required for NLC-only firms |
| 1.4 | Administrative qualification with effective rate, or documented safe-harbor eligibility (federal/specific deliverable only; streamlined may instead accept TxDOT's 120% developed rate) |
| 1.5 | Not precluded — where declared, extends to **subsidiaries and affiliates** of prime and every sub. Not a name match |
| 1.6 | No financial-interest conflict under Govt Code 2261.252(b) |
| 1.7 | E-Verify certification for Texas staff and all assigned subcontractors |
| 1.8 | Revolving-door review for former TxDOT employees (Govt Code 572.054, 2252.901) |

### Tier 2 — people, as of the SOQ deadline (7)

| # | Check |
|---|---|
| 2.1 | PM is a Texas-registered PE *(current check 3 — correct)* |
| 2.2 | PM precertified in >=1 standard work category *(not currently checked)* |
| 2.3 | PM is an employee of the prime, not a sub *(not currently checked)* |
| 2.4 | PM available for interview and not on another short-listed team — "may attend only one interview". A cross-pursuit conflict check |
| 2.5 | **Every standard category has a named task leader who personally holds that precert** |
| 2.6 | Every NLC has a task leader meeting its written minimums |
| 2.7 | Task leaders of designated major categories available for interview; no other personnel may attend |

**2.5 is a defect in the current check 2.** "Team covers all required
categories" is a set intersection — necessary but not sufficient. The
requirement is per category: the individual *named as task leader* must hold
it. A team can collectively cover a category while its named leader does not,
and `&&` returns true.

### Tier 3 — composition arithmetic (4)

| # | Check |
|---|---|
| 3.1 | Category percentages sum to 100 (verified: 68+32, 96+4) |
| 3.2 | Prime self-performs >= the stated minimum with its own workforce — **30% in both**, not the 55% carried from the 2003 LOI. Read per solicitation |
| 3.3 | DBE goal met per sub per service code — counts only if DBE-certified in the NAICS code matching the service provided (541330 engineering, 541370 surveying, 541380 testing labs, 541620 environmental consulting; others for NLCs). Wrong code counts as zero |
| 3.4 | HUB goal met or good-faith effort documented (state) — different program, certification, form and failure mode from DBE |

### Tier 4 — scored, not gated (2)

| # | Check |
|---|---|
| 4.1 | Q&R responses — 90% |
| 4.2 | Past performance from TxDOT database — 10%, not influenceable at bid time |

## 4. Data-model deltas required

1. **Solicitation record** needs: `contract_type`, `process_type`
   (standard/streamlined), `goal_program` (DBE|HUB) + `goal_pct`,
   `min_self_perform_pct` (read, never assumed), `admin_qual_required`,
   `preclusion_declared`, `major_work_categories[]`,
   `interview_attendees_allowed`, `deadline_ts` (time-of-day matters),
   `attachments_required[]`.
2. **`goal_program` must drive two separate check paths.** DBE and HUB are not
   one check.
3. **Per-sub certification records need a NAICS code** and the service it maps
   to, or check 3.3 cannot run.
4. **Task-leader assignment** is a first-class relation: (pursuit, category,
   person), distinct from the team's aggregate precert set.
5. **NLC support:** categories outside the precert taxonomy, with structured
   per-person attributes — years of experience by discipline, licences, roles
   held ("responsible charge", "lead worker", "task leader"), named software
   proficiency. Currently nowhere in the model. 32% of the work on 3362.
6. **Firm affiliate/subsidiary list** for preclusion (1.5).
7. **Past-performance score attaches to a person** as well as a firm (4.2).
8. **Cross-pursuit PM commitment** to detect double-booking (2.4).

## 5. Consequences for the roadmap

1. **Forms move from item 10 to item 1.** At the SOQ stage they are the entire
   submission. They are also far safer to automate than narrative: a form field
   either matches the source record or it does not.
2. **The NLC template is the easiest automation in the system** — its content
   "will not be evaluated" and is used only to test minimums. Pure library
   assembly, no writing quality to get right.
3. **Team composition is a constraint problem, not a checklist.** Percentages
   to 100, prime >= minimum, goal met by qualifying firms in qualifying codes,
   every category assigned to a qualified named leader. Small search space. The
   system should *propose* the team, not merely score one the firm proposes.
   This is the capability worth paying for weekly.
4. **The non-responsiveness checklist (Tier 0) is the highest-value self-serve
   feature.** It is the class of failure where a firm does 60 hours of work and
   is thrown out for a staple or a filename.
5. **Page budgeting was aimed at the wrong stage.** At the SOQ stage the
   constraint is a form field's size, not a page count: generate to the field
   limit, measure the string, reject over-length before a human sees it. No
   rendering step. The earlier rendering-based approach applies only to the
   short-list narrative. Template records need an explicit `stage`.

## 6. Open — what to obtain next

- **The five attachment templates**, especially the **Q&R Template**: it
  defines what is asked, how many questions, and the size of each box. Public,
  attached to every advertised solicitation. Worth more than five more RFQs.
- **A won SOQ** with completed Q&R responses. The solicitation gives the
  required shape; only a winner shows what scored.
- **One currently advertised PEPS solicitation**, to diff against this. Likely
  stale here: the 147.48 average, the 23.7% HUB goal, the 120% indirect rate,
  paper/USB submission mechanics, the short-list stage structure.
- **Volume split, federal-DBE vs state-HUB** — close to two products; decides
  which check path is built first.
- **NLC frequency across typical pursuits** — 32% of one solicitation, 4% of
  the other. Decides whether the intake form needs the new field set (item 5
  above) before it can ship.

---

## 7. Where the source documents live (verified 2026-08-25)

**Current solicitations are not on the URLs printed in the 2018 documents.**
TxDOT moved procurement to the **TxDOT Procurement Portal** at
`https://txdot.bonfirehub.com` — product now called Euna Procurement, formerly
Bonfire, referred to in TxDOT's own material as **eSET** (electronic submittal
and evaluation tool). All three names denote the same system. Everything
advertised after **2020-12-15** is posted there. Open opportunities:
`https://txdot.bonfirehub.com/portal/?tab=openOpportunities`

**The Q&R Template is not a published standalone form.** It is an attachment
inside each solicitation package, behind free vendor registration, and it is
authored per solicitation because the questions vary with the contract. There
is no single template to model — there is a family, and the modelling task is
identifying what is stable across it.

**PEPS advertises in four waves per fiscal year** (September, December, March,
June) and publishes a **fiscal year procurement plan** ahead of them. That
forward pipeline is a better trigger for a qualification check than reacting to
a posting that carries a 14-21 day clock.

### Data sources named in the solicitations (product intake dependencies)

| Need | Source named in the RFQs |
|---|---|
| Firm precert status / Active list | TxDOT list of precertified firms |
| **Per-person precert categories** | **CCIS database, Employee Precertification Categories query, by employee sequence number** — the source for check 2.5 |
| Administrative qualification status | TxDOT administrative qualification list |
| DBE certification + NAICS code | TUCP DBE Directory |
| HUB certification | CPA CMBL / HUB directory, `mycpa.cpa.state.tx.us/tpasscmblsearch` |
| Service code taxonomy | NIGP commodity book (goods/services); NAICS 541xxx for A/E |
| Past performance scores | TxDOT provider evaluation database (internal — not vendor-facing) |

### Verification limits

`txdot.gov`, `dot.state.tx.us` and one third-party mirror are blocked by this
session's egress policy, so TxDOT pages could not be read directly. The portal
migration, the eSET/Euna/Bonfire naming, the post-2020-12-15 cutover and the
four-wave cadence are corroborated across independent search results and one
retrieved TxDOT-issued Bonfire instructions document. **Portal-specific
mechanics in Tier 0 (0.2, 0.3, 0.6) are marked for verification against a live
solicitation and must not be hard-coded until then.**
