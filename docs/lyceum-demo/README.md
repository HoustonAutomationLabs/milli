# Pipeline runs — one fictional firm, two TxDOT solicitations

**Runs:** 601CT0000006541 (2026-09-05) and 601CT0000006549 (2026-09-06).

The second solicitation is the one that matters. One run proves the machinery
works on the case it was built from; two runs tell you whether it works on a case
it was not. 6549 is a different shape — non-federal indefinite-deliverable, 20
awards, no interview, **2** work categories instead of 27, no published preclusion
list, no administrative qualification — and it contradicted four assumptions the
first gate had quietly baked in.

All firm, personnel, licence and project data here is **invented**. The only real
names are the seven firms on TxDOT's published Preclusion Document for this
solicitation; they appear in `gate.py` as data the preclusion check tests
against, and in none of the fabricated submission documents.

## Files

| File | What it is |
|---|---|
| `engine.py` | The checks, parameterised by solicitation. One body, two RFPs. |
| `sol6541.py` | Config: federal specific-deliverable, with interview, 27 categories, 12 pages |
| `sol6549.py` | Config: non-federal indefinite-deliverable, no interview, 2 categories, 10 pages |
| `gate.py` | Original 6541 gate and the fictional firm library `sol6541.py` reshapes |
| `prompts.py` | Coverage of the RFP's named narrative questions (6549 asks four) |
| `q_form.py` | Reads an Attachment 1 questionnaire's response/comment rules from its own hidden sheet |
| `fill6549.py` | Fills Attachment 1 (Q-37NY) for 6549 using those rules |
| `fill6549_sub.py` | Fills Attachment 4 for 6549 **and exports it to PDF**, which is what gets uploaded |
| `fill_forms.py` | Fills Attachments 1 and 4 by writing cell values into the vendor workbooks |
| `checks.py` | Mechanical responsiveness checks (naming, page limit, cross-document consistency) |
| `budget.py` | Page-budget floor **and** ceiling, per section, with a rewrite worklist |
| `solver.py` | Team-composition solver: feasibility, goal ceiling, single-firm sensitivity |
| `out/*.xlsx` | The two filled workbooks — **gitignored by design** (`*.xlsx` is excluded repo-wide so no real export is ever committed). Regenerate with `fill_forms.py`. |
| `out/proposal_draft.md` | The 12-page narrative draft |

```bash
python3 sol6541.py            # gate, first solicitation
python3 sol6549.py            # gate, second solicitation — same engine
python3 budget.py sol6549 out/proposal_6549.md
python3 prompts.py sol6549 out/proposal_6549.md
```

Run order: `solver.py` → `sol<n>.py` → `fill_forms.py` → `checks.py` → `budget.py` → `prompts.py`.
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

## Attachment 4: three defects, one of them TxDOT's

**It is submitted as PDF, on both solicitations.** Both RFPs say it in the same
words — *"The fillable file posted with the solicitation must be completed and
submitted as a PDF file"* — and PEPS recommends Print to PDF to flatten it. The
template is Excel (`601CT0000006541 Subprovider Info.xlsx`, `SUB TEMPL.xlsx`);
the submission is PDF. The `.xlsx` delivered on the first run was non-responsive
on format alone, and check `0.2` passed it because it verified that a file
existed, never that it was the type the slot accepts. The portal's Requested
Information table is the authority: Attachment 1 Excel, Attachments 2–4 PDF.
`0.2b` now enforces it.

**The form has a signature block, and reading named cells never saw it.** Below
the data rows: signature, date, printed name, title, in merged cells beneath
their labels. It became visible only when the sheet was rendered to PDF and read
as a page rather than as cells. The first run's Attachment 4 was unsigned as well
as wrongly formatted, on a document the form itself says "will become part of an
awarded contract".

**The vendor template's print area excludes its own last row.** Print area is
`$A$1:$H$46` on both templates; the answer cells for *Printed (or typed) Name*
and *Title* are on row **47**, under labels on row 46. Fill the form in Excel,
Print to PDF exactly as PEPS recommends, upload — and those two fields are blank
in the submitted document however carefully they were typed. This is a defect in
TxDOT's file and it lands entirely on the bidder. The fix extends the print area
by one row, changing no content and no structure.

None of the three was findable by reading cells. All three needed the file
rendered the way a reviewer sees it, then compared against its own source.

## The two questionnaires are identical except for one invisible flag

Q-59ES (6541) and Q-37NY (6549) are the same form to the eye: same 26 rows, same
question numbers, same two dropdowns on the same cell ranges, same locked cells,
same visible instructions, and identical question text on 25 of 26 rows — the
26th differs by a colon. Only the Euna question IDs change, as instance
identifiers should.

They disagree in exactly one place, a boolean in a sheet whose state is
`veryHidden`, which Excel will not offer in the unhide dialog:

| dropdown group | 6541 (Q-59ES) | 6549 (Q-37NY) |
|---|---|---|
| certification rows 16–23 (YES/NO) | comment must be blank | comment must be blank |
| submittal rows 33–36 (INCLUDED / NOT INCLUDED) | **comment must be blank** | **comment optional** |

Nothing visible in either file says so. A firm that learned the rule on one
solicitation and applied it to the next would be applying a rule that no longer
holds. In this direction the mistake is harmless, since a blank comment
satisfies both. The mechanism is not harmless: column 2 of the same hidden table
is a **comment REQUIRED** flag, and a form with it set reports "A comment is
required for this response" on a row the firm answered correctly, with no
visible instruction explaining why.

So `q_form.py` never hardcodes the rule — it decodes the hidden table (col 1
permitted value, col 2 comment-required, col 3 comment-must-be-blank), maps
dropdown rows to groups from the sheet's own data validations, and applies what
it finds. `checks.py` was carrying the hardcoded version; it passed on 6541 and
would have misreported on 6549, and now reads the form instead.

**This is the clearest argument in the whole exercise for automating this work.**
The document carries machine-readable constraints that a careful human reader
cannot see, and they change between solicitations that look the same.

One inference is flagged rather than asserted: free-text answers are written to
the **Comment** column, because the Response column is pre-filled with `-` on
those rows and the status formula treats `-` as equivalent to blank — which only
makes sense if `-` marks "no dropdown applies here". That is read off the
formula, not documented anywhere, and a real submission should confirm it with
the procurement engineer.

## What the second solicitation broke

**Four assumptions, all wrong.** The first gate treated as universal: that
administrative qualification is required (6549 s.11 — not required to compete);
that preclusion arrives as a published list of firm names (6549 s.6 — the rule
only, no list, because statewide scope has no project list to match); that there
is an interview with major categories (6549 — none, the written proposal is the
entire evaluation); and that a work category is performed by one firm.

**The one-firm-per-category model cannot express this contract.** Both RFPs ask
for "the percentage of work anticipated for each firm for each category" — a
matrix, not a mapping. With 27 categories every one happened to sit with a single
firm and the difference was invisible. With two categories at 80/20 it is
structural: the prime cannot reach its 30% self-performance floor out of the 20%
management category, so it must hold a slice of the 80% inspection category, and
that slice only exists if a category can be split. `ALLOCATION` is now
`{category: {firm: percent}}` with the task leader tracked separately, because
there is still exactly one task leader per category however many firms perform it.

**A check whose precondition is absent must report N/A, never PASS.** This is the
design rule the second solicitation forced. "No precluded firm on the team"
evaluated against an empty list is not a finding, it is the absence of one, and
printing PASS beside it tells a reader the team was screened when nothing was.
The engine now separates four outcomes — pass, fail, not-applicable, and MANUAL
for a real requirement no code can decide — and the headline count counts only
what was actually verified. 6541: 22 verified, 3 n/a, 1 manual. 6549: 20
verified, 4 n/a, **2** manual, the extra one being preclusion, which on this
solicitation is a question only the firm can answer.

**The weights invert.** Planning leads on 6541 at 30 with technical approach
trailing at 22; on 6549 key staff leads at 30 and technical approach is 29 while
planning drops to 20. Page limit 12 becomes 10. A firm reusing last quarter's
page budget writes its longest section on the criterion that fell furthest.

**6549 asks four questions by name**, three demanding a worked example, where
6541 gave general guidance. That is a new and checkable failure class — an
unanswered named question is a scoring zero on a criterion, not a weak paragraph
— so `prompts.py` verifies each is addressed and reports honestly that its
example detection is a heuristic a vague sentence can satisfy.

**Attachment 4 is a fillable PDF on 6549, not Excel.** `fill_forms.py` is an
openpyxl cell-writer and does not apply. The Excel path is not the general case.

**What did generalise:** the format rules are identical apart from the page
limit; the 30% self-performance floor; the January–March annual renewal window;
the PM must be a Texas P.E. employed by the prime; the four-attachment package
shape; and Attachment 3 remains impossible to produce outside CCIS.

## Second-run results (601CT0000006549)

- **Gate: GO.** 20 verified, 0 failed, 4 not applicable, 2 needing a human
  answer. Prime self-performs 45% against the 30% floor, taking 20% (management)
  plus 25% of the 80% inspection category across a three-region subprovider team.
- **Narrative: 92% of budget**, 9.4 of 10 pages — against 51% on the first run.
  First pass reached 78% because it was written per section against a stated word
  count from the start; two targeted passes closed the rest. The method the first
  run inferred, applied deliberately, roughly halved the gap it had to close.
- **Prompts: 4 of 4** named questions answered, both required worked examples
  present.
- **Attachment 1 filled and audit-clean.** Protection, both validations and the
  status formulas preserved; filename 25/25 characters. Rows 35 and 36 answer
  **NOT INCLUDED** — the PTC form cannot be produced outside CCIS and the
  Subprovider PDF was not supplied, and answering INCLUDED for a file that is
  not in the package would be a false statement on a form the project manager
  certifies (RFP s.28: a false statement may void the response).
- **One of four attachments producible here**, for two different reasons:
  Attachment 3 is CCIS-only on both solicitations, and Attachment 4 is a
  fillable PDF on 6549 rather than the Excel workbook 6541 supplied.

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
