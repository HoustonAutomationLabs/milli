# End-to-end pipeline run — fictional firm vs. 601CT0000006541

**Run:** 2026-09-05. Full report published as an artifact.

All firm, personnel, licence and project data here is **invented**. The only real
names are the seven firms on TxDOT's published Preclusion Document for this
solicitation; they appear in `gate.py` as data the preclusion check tests
against, and in none of the fabricated submission documents.

## Files

| File | What it is |
|---|---|
| `gate.py` | Solicitation parameters, fictional firm library, allocation, and the 20-check gate |
| `fill_forms.py` | Fills Attachments 1 and 4 by writing cell values into the vendor workbooks |
| `checks.py` | Mechanical responsiveness checks (naming, page limit, cross-document consistency) |
| `budget.py` | Page-budget floor **and** ceiling, per section, with a rewrite worklist |
| `solver.py` | Team-composition solver: feasibility, goal ceiling, single-firm sensitivity |
| `out/*.xlsx` | The two filled workbooks — **gitignored by design** (`*.xlsx` is excluded repo-wide so no real export is ever committed). Regenerate with `fill_forms.py`. |
| `out/proposal_draft.md` | The 12-page narrative draft |

Run order: `solver.py` → `gate.py` → `fill_forms.py` → `checks.py` → `budget.py`.
`fill_forms.py` and `checks.py` need `openpyxl`; the other two are stdlib only.
`budget.py` and `checks.py` exit non-zero on a failure, so they can gate a build.

## Results

- **Gate: GO, 20/20.** Prime self-performs 64% against a 30% minimum; all 27
  categories have a named leader who personally holds the precertification;
  percentages total 100.
- **Forms: 2 of 3 producible attachments filled and verified.** Sheet
  protection, both data validations and the status formulas all preserved.
  Filenames land at exactly 25 of 25 permitted characters.
- **Narrative: 72% of budget** after one corrective pass, from 51% on the first.
- **Mechanical: 10/11.** The single failure is the PTC form, which cannot be
  produced outside CCIS.
- **Budget: FAIL, 3 of 4 sections short.** The draft that passes every other
  check fails this one. Section 2, the only section that got a targeted rewrite,
  is the only section that passes — at 90%.
- **Solver: feasible, and every subprovider is load-bearing.** It reproduces the
  hand-built allocation to within two categories, and both of its disagreements
  are corrections.

## Findings

**The substring collision is live in this solicitation.** It requires both
`1.8.1` Public Involvement and `11.8.1` Construction Schedule Support, and
`"1.8.1"` is a substring of `"11.8.1"`. A containment matcher credits the
scheduling lead with the public involvement qualification. Store and compare
precertifications as codes.

**The preclusion document is a named firm list** — seven firms from the design
contract, extended to subsidiaries and affiliates, so the check is a name match
plus affiliate expansion. Note that 4.5.1 Constructability Review is required
here and the firm that performed constructability review on the design contract
is barred: the obvious specialist is the disqualifying one. The list also warns
it is "not inclusive," leaving the prime an open-ended duty on adjacent projects.

**A rule exists only in the questionnaire's hidden sheet.** Both dropdown values,
on certifications and submittal contents alike, are marked
comment-must-be-blank. Typing anything helpful in the comment column of those
twelve rows makes the status cell report an error. The visible instructions do
not say this.

**The subprovider form wants every firm contacted for teaming,** not only those
engaged, with a column distinguishing them. That evidence trail exists even with
no goal programme and cannot be reconstructed after the fact — it needs a
lightweight teaming log in intake.

**First-pass narrative generation undershoots by about half.** 51% of budget,
and unevenly: the two heaviest-weighted criteria came in lowest. A targeted
per-section rewrite against a measured word target took one section from 40% to
92% in a single pass; bulk additions reached only 63-72%. Generate per section
against a stated word count, measure, then run one targeted corrective pass.

**Under-length must be a failing check.** Every control in the process catches
overflow — page limits, allotted space, excess pages removed. Nothing catches
leaving scored space unused, which is the more common and more expensive error.
`budget.py` now enforces a floor at 90% of each section's weight-derived target
and prints a per-section word deficit ranked by the points left uncontested,
because the deficit is the input to the rewrite that measurably works.

## What the solver found

**Losing any one of the six subproviders makes the bid infeasible.** Not weaker
— infeasible. Twenty-two of twenty-seven categories have exactly one qualified
leader in the entire library, so six of six departures are fatal, costing between
2% and 15% of the work. A team assembled to cover the scope exactly has no
redundancy anywhere, and nobody notices until a firm withdraws.

**The DBE goal ceiling is 20%.** Only two firms in the library are certified,
and the categories they can lead account for a fifth of the work. Any goal above
that is unreachable by rearrangement, which is a do-not-bid answer available on
day one instead of after six teaming conversations. This solicitation assigns no
goal; the next one in the family may.

**The solver exposed an unstated constraint by exploiting it.** Its first version
satisfied every stated rule and made the Project Manager task leader for three
categories totalling 35% of the work. Nothing in the solicitation forbids it, and
no evaluator would score it well — key-staff experience is 26 points and project
planning 30, both read as questions about depth. A concentration cap and a PM
exclusion are now in the model, **marked as judgement parameters rather than
requirements**, because that is what they are. With them in place the solver
disagrees with the hand-built team in two categories, and in both it is right:
the human-authored allocation had also quietly put the PM in a task-leader slot.

## Bugs the run found (two in the checks themselves)

1. **Goal-certification check fired with no goal assigned.** The gate returned
   NO-GO on a lapsing HUB certificate, but this solicitation assigns no goal, so
   the lapse cannot make the response non-responsive. Now conditional on
   `goal_program`, still reported as advisory.
2. **The "Task Leader" consistency check flagged pronouns as people** — `He`,
   `She`, `Differing`. A naive regex produces false positives at a rate that
   makes the check useless. Tightened to require an honorific, a credential
   suffix, or a known surname.
3. **The page-budget guidance was aimed at the wrong failure.** Compression was
   specified; expansion is what is actually needed. The compression pass would
   never have fired.

## Where automation stops

Attachment 3, the Project Team Composition form, is generated inside TxDOT's
Salesforce (CCIS), completed there and downloaded. It cannot be produced from
outside. The honest offer is three of four attachments prepared plus the data the
fourth needs, with the client spending ~20 minutes in CCIS — where TxDOT's
picklist independently confirms the precertification matching, making it a check
on the team rather than pure overhead.
