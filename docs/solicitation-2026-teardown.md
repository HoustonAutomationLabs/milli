# 601CT0000006541 — live 2026 solicitation teardown

**Analysed:** 2026-09-05. Sources: the RFP PDF and the Attachment 1 Cover Page
(Q-59ES) Excel questionnaire, plus the portal's Requested Information panel.
CEI services, SH 45 at I-35 direct connections. Posted 2026-09-01, 21-day
window, proposals due 2026-09-22 1:00 p.m. CT, questions close 2026-09-08.
Federal process with interview, **no DBE goal**.

Supersedes parts of `docs/txdot-soq-gate-spec.md`, which was derived from two
2018 RFQs.

No firm or personnel data. TxDOT staff names omitted.

---

## 1. Two findings that reset the roadmap

**The questionnaire is machine-fillable.** The Q&R Template is gone. Attachment
1 is a Euna questionnaire exported as a locked `.xlsx` with a completely regular
structure: stable numeric question ID per row, response cell driven by two-value
data validation, free-text comment cell, formula-driven status cell. Filling it
is writing two columns on known rows.

**The narrative is back, and it is first-stage.** This is an RFP, not an RFQ.
Attachment 2 is a written proposal of **max 12 pages**, and the short list is
decided on it. The 2018 two-step (SOQ then proposal) has collapsed into one.
Drafting is not downstream of a gate — it *is* the first stage. Which process a
solicitation uses must be read from the document.

## 2. Package contents — 4 required uploads

| Attachment | Format | Source | Automatable |
|---|---|---|---|
| 1 Cover Page (Q-59ES) | .xlsx | Portal download, fill in Excel, upload as Excel | Fully |
| 2 Proposal | .pdf | Written. Single PDF, no attachments, 12 pages | Drafted then edited |
| 3 Project Team Composition (Parts 1-3) | .pdf | **Generated in Salesforce (CCIS)**, downloaded | No — TxDOT owns it |
| 4 Subprovider Contact Information | .pdf | Fillable file from portal | Fully |

No HSP (federal). **No DBE goal at all.** No NLCs — all 27 work categories are
standard, including construction schedule support which was an NLC in 2018.
TxDOT appears to be absorbing NLCs into the standard taxonomy, shrinking a gap
previously flagged in the data model. Category percentages verified to sum to 100.

## 3. Questionnaire structure

Sheets: `Instructions`, `Summary`, `1`, `Response Options (hidden)`. All
protected. Instructions state that changing the structure, using formulas, or
saving in another format **invalidates the submission**.

Sheet `1`, 22 rows in four blocks. Columns: B = question ID (e.g. `1862067`),
C = code, D = question text, F = response, G = comment, H = computed status.

- **GENERAL** (1.1.1-1.1.3, free text): prime legal firm name; Texas
  Identification Number (TIN, or EIN, or NONE — explicitly *not* the PTC Vendor
  ID); **CCIS Seq ID**.
- **CERTIFICATION** (1.2.1-1.2.8, dropdown `YES|NO`): licensing board
  registration; employees of prime or identified sub; PE/RA/PLS signs and seals;
  Secretary of State registration under the legal name; **>=30% self-performance**;
  no 2261.252(b) financial interest; not precluded under 43 TAC §10.6;
  **NDAA §889 / §1260H / foreign-adversary ownership or control** (new since 2018).
- **ATTESTATION** (1.3.1-1.3.7, free text): PM full name (submitting the
  questionnaire is the certification — no wet signature); date certified; PM
  TBPELS/TBAE licence number; firm registration number; **PM email** (short-list
  and selection notices go here, *not* through the portal); PM address; PM phone.
- **RESPONSE SUBMITTAL CONTENTS** (1.4.1-1.4.4, dropdown `INCLUDED|NOT INCLUDED`).

**"A 'NO' response will disqualify the submittal from competition."** Eight
certification rows are a hard gate — and they are exactly the conditions the
intake questionnaire collects, which is the argument for checking at onboarding
rather than at deadline.

Implementation note: response cells carry Excel data validation naming exactly
two permitted values, and question IDs are stable identifiers rather than
positions. Write values into cells; **never regenerate the workbook** —
protection, validation and formulas must survive.

## 4. Evaluation weights and page budget

| Criterion | Weight |
|---|---|
| Project planning & management (staffing, resource mgmt, communication plan, QC, sub utilisation) | 30 |
| Key staff's relevant experience | 26 |
| Technical approach (understanding, approach, innovative concepts) | 22 |
| PM's relevant experience | 15 |
| Past performance (from PS-CAMS, not written by the firm) | 7 |
| **Total** | **100** |

Planning and management outweighs technical approach. A firm allocating 12 pages
by instinct misallocates roughly a third of them.

93 points are narrative-influenced, so the budget divides:

| Section | Pages | ~Words @550/pg |
|---|---|---|
| Project planning & management | 3.87 | 2,130 |
| Key staff experience | 3.35 | 1,845 |
| Technical approach | 2.84 | 1,560 |
| PM experience | 1.94 | 1,065 |

## 5. Formatting rules — a deterministic checker

- 12 pages max, counted from the first page of the PDF. Excess pages **removed
  and not scored**.
- **No cover page, letter, or table of contents** — prohibited outright.
- Prime firm name, solicitation number, and page number **on every page**.
- Legible at 8.5x11, 11-pt Calibri recommended; unreadable text ignored. Min
  0.5" margins; text outside ignored.
- No hyperlinks, QR codes, or external references.
- Shrinking margins/fonts to cram content is called out; reviewers may score
  presentation down.

**Cross-document consistency (non-responsive if violated):**
- PM in the proposal must match PM on the questionnaire.
- Task leader in the proposal must match the PTC form for that work category —
  unless both are at the same firm and both precertified in it.
- **Do not use "Task Lead"/"Task Leader" in the narrative for anyone not
  precertified and listed on the PTC form for that category.** A loose phrase
  becomes a responsiveness defect. Mechanical, and no human proofreader
  reliably catches it.

## 6. Corrections to the 2018-derived spec

1. **"At the SOQ stage there is no narrative document"** — true of 2018 RFQs,
   false here. Process type must be read per solicitation.
2. **File naming changed** (was flagged unverified — now answered). 2018: first
   **15** chars + `_Complete`. 2026: first **12** chars, per-attachment suffix,
   whole filename capped at **25 characters**:
   `ZEBRA ENGINE_001234_Att 1.xlsx` — exactly 25, at the cap, not under it.
3. **Federal does not imply a DBE goal.** This contract is federally funded with
   no goal assigned. `goal_program` needs at least three values; "it's federal"
   does not populate it.
4. **Past performance is less forgiving.** 2018 default was 147.48/150 ≈ 98% of
   available points. Now banded (>80→5, 60-80→4, 40-60→3, 20-40→2, floor 20);
   default ESA 75.8 puts a newcomer at 4/5. History matters more. PM score still
   follows the person between employers.

## 7. The keystone insight, partly deflated

From the precertification section: *"Individual precertification status will be
verified when entering Task Leaders in the PTC Form. The form automatically
generates a picklist of eligible firms and staff that have been precertified in
the work category."*

The PTC form is built inside TxDOT's Salesforce and **will not permit naming a
task leader who does not hold the category**. The check previously identified as
the highest-consequence item in the gate is enforced by the agency before a
submission is assembled.

Value moves upstream of the form:
- **Bid/no-bid in an hour, not a week.** The picklist reveals a gap only once a
  firm is deep in the form.
- **Which partner closes the gap** — the picklist says no, not who to call.
- **Composition under four simultaneous constraints.** TxDOT validates one.
- **The narrative** — now the entire first-stage score, untouched by TxDOT tooling.

The most defensible-feeling part of the product is partly automated by the
agency already. The riskiest-feeling part — the writing — is where the score is
decided.

## 8. Section 37 — data security flowdown

Providers selected for award must complete a **TxDOT Security Questionnaire**
and meet identified security controls **before entering negotiations**; failure
may exclude the response. Government Code §2054.138 flowing down through the
contract.

If a client wins and Lyceum holds the material that went into the proposal,
Lyceum sits inside that boundary. This raises the security rewrite from
reputational to contractual. It is also a sales asset once true: obtain the
TxDOT Security Questionnaire and data classification policy, answer honestly for
Lyceum, and hand prospects something competitors will not have.

## 9. To obtain next

1. **Subprovider Info (.xlsx)** — attachment 4's structure; the last unseen
   required upload. Likely another regular workbook, which would make three of
   four attachments fully automatable.
2. **Attachment I, Information Resources and Security Requirements** — the
   controls that flow down; answers what §37 demands.
3. **Preclusion document** — how preclusion is actually expressed (firm list,
   project list, other). Determines whether the affiliate check is buildable.
4. **Attachment C, Services to be Provided by the Engineer** — the scope the
   narrative must show understanding of; raw material for a drafting test.

Still unavailable: the **PTC form** (generated in CCIS, not downloadable — the
Vendor Contact CCIS Job Aid is the next best thing) and a **winning proposal**,
still the highest-value document in the project.
