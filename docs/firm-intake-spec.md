# Firm qualification intake — field specification

**Drafted:** 2026-08-25. Derived from `docs/txdot-soq-gate-spec.md`; every field
traces to a numbered check there.

Serves three purposes with one definition: the manual onboarding questionnaire,
the self-serve profile form spec, and the database schema.

Collect A, B and C **once per firm** (firm library data is durable). Collect D
**once per pursuit**.

No firm or personnel data. Prototype must be populated with a fictional firm.

---

## A. Firm

### Identity — must match across three systems

| Field | Check |
|---|---|
| Legal name exactly as registered with the Texas Comptroller | 1.2 |
| Any dba, and whether it is the name on the admin qualification list | 1.2 |
| Texas Secretary of State registration — number, status | 1.2 |
| **TxDOT firm sequence number** — closest thing to a stable firm id; removes name matching | 1.3 |
| TX Board of Professional Engineers registration — number, status, renewal date | 1.1 |

### Standing with TxDOT — all dated, none boolean

| Field | Check |
|---|---|
| Precert status + date of last annual renewal (window: 1 Jan – 31 Mar). Missing it costs Active status for the year — **calendar alert worth owning** | 1.3 |
| Firm-level approved precert categories (distinct from individuals') | 2.5 |
| Administrative qualification — status, effective indirect rate, expiry; or safe-harbor eligibility; or decision to accept TxDOT's developed rate | 1.4 |
| Known firm past-performance score, if any. A poor score is worse than no score (no score defaults to the 5-year average) | 4.2 |

### Goal-program certifications — two programs, never one field

| Field | Check |
|---|---|
| DBE certification — agency, expiry, **and every NAICS code certified in**. Wrong code counts as zero toward a goal | 3.3 |
| HUB certification — VID, file/vendor number, approval date, expiry | 3.4 |
| Which services the firm offers as a sub, and under which code | 3.3 |

### Disclosures — ask at intake, not at deadline

| Field | Check |
|---|---|
| Subsidiaries, affiliates, parent companies — preclusion disqualifies the corporate family, not the named entity | 1.5 |
| Current and recent design work by project (what preclusion tests against) | 1.5 |
| Former TxDOT employees on staff — name, role, date left | 1.8 |
| Financial relationships potentially conflicting under Govt Code 2261.252(b) | 1.6 |
| E-Verify enrolment | 1.7 |

## B. Each person

Collect for everyone who might lead a category, not only the usual PM.

### Identity and credentials

| Field | Check |
|---|---|
| Full legal name as it appears in TxDOT records | 2.5 |
| **CCIS employee sequence / personnel record number** — the single most valuable field; how per-person precert is queried, and it removes name matching from the highest-consequence check | 2.5 |
| Texas PE licence — number, status, expiry | 2.1, 2.6 |
| Out-of-state licences; other credentials (RPLS, AICP, PTOE) with current/inactive status | 2.6 |
| Employer — prime, or which subprovider. Decides which firm can lead a team | 2.3 |

### Precertification

| Field | Check |
|---|---|
| Approved categories — stored and compared **as codes, never as text** (`18.2.1` contains `8.2.1`) | 2.2, 2.5 |
| Denied categories — a denial is not a blank; surfaces as a named risk | 2.5 |
| Pending categories, with date applied | 2.5 |

### Experience — for non-listed categories (NEW: not in the model today)

| Field | Check |
|---|---|
| Years of experience, total **and by discipline** — minimums are discipline-specific | 2.6 |
| Roles held with years in each — "responsible charge", "lead worker", "task leader" are terms of art, not synonyms | 2.6 |
| Named software proficiency (e.g. Primavera or equivalent, plus one of Claim Digger / Schedule Analyzer / Acumen Fuse) | 2.6 |
| Public involvement and other non-engineering experience — 20% of the work on one solicitation reviewed | 2.6 |

### Availability

| Field | Check |
|---|---|
| Known PM past-performance score — follows the person between employers | 4.2 |
| % committed to each active contract and live pursuit (feeds the staff time-commitment table) | 2.7 |
| Which pursuits this person is already named PM on — **may attend only one interview**; a cross-pursuit check no per-pursuit spreadsheet can catch | 2.4 |

## C. Teaming partners

Subs never onboard; the prime supplies their documents as it already does during
teaming. Collect the A firm block and the B person block (leaders only), plus:

| Field | Check |
|---|---|
| Which categories this partner would lead, at what percentage | 3.1, 3.3 |
| Date the partner's certifications were last verified — they lapse and **the prime is disqualified** | 1.3, 3.3 |

## D. Each pursuit

| Field | Check |
|---|---|
| Solicitation number, agency, district/division | — |
| Submittal deadline — **date and time**; every other check evaluates as of this moment | all |
| Contract type and process type (specific/indefinite; standard/streamlined) | 1.4 |
| Goal program + percentage — **one field, two separate check paths** | 3.3, 3.4 |
| Minimum prime self-performance % — read per solicitation; assuming it is a defect | 3.2 |
| Required standard categories, each with percentage | 2.5, 3.1 |
| Non-listed categories with minimum requirements **verbatim** — paraphrasing loses deciding detail | 2.6 |
| Which categories are designated major | 2.7 |
| Whether a preclusion is declared | 1.5 |
| Required attachments; questions deadline (~1 week before submittal) | 0.2, 0.7 |

## E. Decisions before this goes to a client

1. **Who fetches what.** Several fields live in TxDOT systems, not the firm's
   files (precert categories, admin qualification, past performance). Asking a
   client for what you can look up is the main reason questionnaires come back
   half-empty. Decide per field; ask only for the remainder.
2. **Day-one subset.** Identity + precert + PM + goal certifications answers the
   qualification question for most pursuits. The rest can fill in over weeks. A
   firm that abandons a 40-minute form has not been onboarded.
3. **Where it goes.** This is competitive information — teaming, pipeline, gaps.
   Two firms in the system may bid the same contract. That is the argument for
   tenant isolation before client #2, and it must be answerable when a prospect
   asks.

## F. Open questions (answerable from the portal, not from a client)

- **Can per-person precertification be pulled in bulk, or only one employee at a
  time?** Decides whether intake is a form a firm fills in or a file it uploads.
  Largest open question in the design.
- **Does the precert report a firm can download for itself already contain the
  sequence numbers?** If so, most of section B becomes automatic.
