"""
Read a TxDOT Attachment 1 questionnaire's OWN rules instead of assuming them.

Two questionnaires, Q-59ES (601CT0000006541) and Q-37NY (601CT0000006549), are
identical to the eye. Same rows, same question numbers, same question text on 25
of 26 rows, same two dropdowns, same locked cells, same visible instructions.
They differ in one place: a boolean in a sheet whose state is `veryHidden`,
which Excel will not show in the unhide dialog.

    certification rows (YES/NO)          comment must be blank   BOTH forms
    submittal rows (INCLUDED/NOT INC.)   comment must be blank   6541 only
                                         comment optional        6549

Nothing visible in either file says so. A firm that learned the rule on one
solicitation and carried it to the next would be applying a rule that no longer
holds. In this particular direction the mistake is harmless -- a blank comment
satisfies both -- but the same mechanism carries a `comment REQUIRED` flag,
column 2 of the same table, and a form with that flag set would report "A
comment is required for this response" on a row the firm had answered
correctly, with no visible instruction explaining why.

So the rule is never hardcoded. It is read from the workbook, per row, at fill
time. That is the whole argument for automating this class of work: the document
carries machine-readable constraints that a careful human reader cannot see.

Layout of the hidden table, decoded from the status formula in column H:
    col 1  the permitted response value
    col 2  TRUE -> a comment is REQUIRED for this response
    col 3  TRUE -> the comment MUST BE BLANK for this response
    row 3  the human-readable option list used in the error message
"""
import re

HIDDEN = "Response Options (hidden)"
SHEET = "1"
COL_RESPONSE, COL_COMMENT, COL_STATUS = "F", "G", "H"


def _truth(v):
    """Cells hold the formulas =TRUE() / =FALSE(), not booleans."""
    if isinstance(v, bool):
        return v
    return str(v).strip().upper().replace("=", "").replace("()", "") == "TRUE"


def read_rules(wb):
    """{group_index: {response_value: (comment_required, comment_must_be_blank)}}"""
    h = wb[HIDDEN]
    groups = {}
    for gi, base in enumerate(["A", "D"]):
        cols = [chr(ord(base) + i) for i in range(3)]
        g = {}
        for r in (1, 2):
            val = h[f"{cols[0]}{r}"].value
            if val in (None, ""):
                continue
            g[str(val)] = (_truth(h[f"{cols[1]}{r}"].value),
                           _truth(h[f"{cols[2]}{r}"].value))
        groups[gi] = g
    return groups


def dropdown_rows(ws):
    """{row: group_index} from the sheet's own data validations, in the order the
    validations appear -- which is the order the status formulas reference as
    responseOption0 and responseOption1."""
    out, seen = {}, []
    for dv in ws.data_validations.dataValidation:
        opts = tuple(sorted(str(dv.formula1).strip('"').split(",")))
        if opts not in seen:
            seen.append(opts)
        gi = seen.index(opts)
        for rng in str(dv.sqref).split():
            m = re.match(r'[A-Z]+(\d+):[A-Z]+(\d+)', rng) or re.match(r'[A-Z]+(\d+)$', rng)
            lo = int(m.group(1))
            hi = int(m.group(2)) if m.lastindex and m.lastindex > 1 else lo
            for r in range(lo, hi + 1):
                out[r] = gi
    return out


def free_text_rows(ws, drops, lo=11, hi=36):
    """Answerable rows that are not dropdowns and not section headers. A header
    row has no question number in column C of the form N.N.N."""
    out = []
    for r in range(lo, hi + 1):
        if r in drops:
            continue
        if re.match(r'^\d+\.\d+\.\d+$', str(ws[f"C{r}"].value or "").strip()):
            out.append(r)
    return out


def describe(wb):
    ws, rules, drops = wb[SHEET], read_rules(wb), dropdown_rows(wb[SHEET])
    return dict(rules=rules, dropdowns=drops,
                free_text=free_text_rows(ws, drops))


def fill(ws, rules, drops, free_text, dropdown_answers, text_answers):
    """Write answers and return the rows where the form's own rules were applied.

    Free text goes to the COMMENT column. The response column is pre-filled with
    "-" on those rows and the status formula treats "-" as equivalent to blank,
    which only makes sense if "-" marks 'no dropdown applies here' -- so the
    answer belongs in the comment. This is inference from the formula, not a
    documented rule; it is the one part of this map that a real submission should
    confirm with the procurement engineer.
    """
    applied = []
    ws.protection.sheet = False
    for r, gi in sorted(drops.items()):
        val = dropdown_answers.get(r)
        if val is None:
            continue
        ws[f"{COL_RESPONSE}{r}"] = val
        required, must_blank = rules[gi].get(val, (False, False))
        if must_blank:
            ws[f"{COL_COMMENT}{r}"] = None
            applied.append((r, val, "comment cleared — form requires blank"))
        elif required:
            applied.append((r, val, "COMMENT REQUIRED by the form — supply one"))
        else:
            applied.append((r, val, "comment optional"))
    for r in free_text:
        if r in text_answers:
            ws[f"{COL_COMMENT}{r}"] = text_answers[r]
    ws.protection.sheet = True
    return applied


def audit(ws, rules, drops, free_text):
    """Re-read a filled sheet and report every row the form would mark wrong."""
    problems = []
    for r, gi in sorted(drops.items()):
        val = str(ws[f"{COL_RESPONSE}{r}"].value or "").strip()
        cmt = str(ws[f"{COL_COMMENT}{r}"].value or "").strip()
        if not val:
            problems.append((r, "no response selected")); continue
        if val not in rules[gi]:
            problems.append((r, f"{val!r} is not a permitted option")); continue
        required, must_blank = rules[gi][val]
        if must_blank and cmt:
            problems.append((r, "comment must be blank for this response"))
        if required and not cmt:
            problems.append((r, "a comment is required for this response"))
    for r in free_text:
        if not str(ws[f"{COL_COMMENT}{r}"].value or "").strip() and \
           str(ws[f"{COL_RESPONSE}{r}"].value or "").strip() in ("", "-"):
            problems.append((r, "unanswered"))
    return problems
