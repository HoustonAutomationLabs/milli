"""
Page-budget checker: fails a section for being SHORT, not only for overflowing.

The end-to-end run found the failure this exists to catch. Every control in the
TxDOT process guards the ceiling — a 12-page limit, a font floor, a margin
minimum — and nothing guards the floor. The first-pass narrative came in at 51%
of its weight-derived budget, six pages against twelve, on criteria worth 93 of
100 points. No mechanical check fired, because none of them was looking down.

Under-length is also the more expensive error. Overflow is caught by the agency
and by the author, who can see the page count. Undershoot is invisible: the
document reads as finished, and the points are simply never contested.

The remedy the run measured: a targeted rewrite against a stated word target
took one section from 40% to 92% in a single pass, while bulk additions across
the whole document reached only 63-72%. So this reports a per-section word
deficit rather than a document-level percentage — the deficit is the input to
the rewrite that actually works.

Run: python3 budget.py            (exit 1 if any section is out of band)
"""
import re, sys

NARR = "out/proposal_draft.md"
WORDS_PER_PAGE = 550
PAGE_LIMIT = 12

# Weight of each scored criterion, from the solicitation's evaluation table.
# Keyed by the narrative's section number.
WEIGHTS = {1: 22, 2: 15, 3: 30, 4: 26}

# A section may run to its budget but not past it (the page limit is hard), and
# may not fall below FLOOR of it (scored space left uncontested).
FLOOR, CEILING = 0.90, 1.00


def words(text):
    """Count prose words the way a page estimate would see them: markup and
    the budget annotation itself are not words on the page."""
    text = re.sub(r'\*Budget:[^*]*\*', ' ', text)
    text = re.sub(r'^\s*[#>]+\s*', ' ', text, flags=re.M)
    text = re.sub(r'[*_`|]', ' ', text)
    text = re.sub(r'^\s*[-=]{3,}\s*$', ' ', text, flags=re.M)
    return len(text.split())


def sections(doc):
    """Split on level-2 headings, keeping each section's declared budget."""
    parts = re.split(r'^## +', doc, flags=re.M)[1:]
    out = []
    for p in parts:
        title = p.split("\n", 1)[0].strip()
        num = int(re.match(r'(\d+)', title).group(1)) if re.match(r'\d', title) else None
        m = re.search(r'\*Budget:\s*([\d.]+)\s*pages?\s*/\s*~?([\d,]+)\s*words?', p)
        target = int(m.group(2).replace(",", "")) if m else None
        out.append(dict(num=num, title=title, target=target, actual=words(p)))
    return out


def main():
    doc = open(NARR).read()
    secs = sections(doc)
    budgeted = [s for s in secs if s["target"]]

    print("=" * 78)
    print("PAGE BUDGET — floor and ceiling")
    print("=" * 78)
    print(f"  {'§':<3}{'section':<34}{'target':>8}{'actual':>8}{'fill':>7}  verdict")

    failures, worklist = [], []
    for s in budgeted:
        fill = s["actual"] / s["target"]
        short = fill < FLOOR
        over = fill > CEILING
        verdict = "SHORT" if short else "OVER" if over else "ok"
        if short or over:
            failures.append(s)
        if short:
            deficit = round(s["target"] * FLOOR) - s["actual"]
            worklist.append((WEIGHTS.get(s["num"], 0) * (1 - fill), s, deficit))
        name = s["title"][:33]
        print(f"  {s['num']:<3}{name:<34}{s['target']:>8,}{s['actual']:>8,}"
              f"{fill:>6.0%}  {verdict}")

    total_t = sum(s["target"] for s in budgeted)
    total_a = sum(s["actual"] for s in budgeted)
    doc_words = words(doc)
    print("-" * 78)
    print(f"  {'':3}{'budgeted sections':<34}{total_t:>8,}{total_a:>8,}"
          f"{total_a/total_t:>6.0%}")
    print(f"  whole document ~{doc_words/WORDS_PER_PAGE:.1f} pages "
          f"of {PAGE_LIMIT} at {WORDS_PER_PAGE} words/page")

    if worklist:
        print()
        print("REWRITE WORKLIST — most unused scored space first")
        print("  Rewrite one section against its word target, then re-measure. The")
        print("  run showed a targeted pass reaches ~92% of budget where bulk")
        print("  additions across the document reach only 63-72%.")
        for stake, s, deficit in sorted(worklist, reverse=True, key=lambda x: x[0]):
            w = WEIGHTS.get(s["num"], 0)
            print(f"    § {s['num']} {s['title'][:40]:<42} +{deficit:>5,} words"
                  f"   {stake:.1f} of {w} pts uncontested")

    print("=" * 78)
    if failures:
        print(f"FAIL — {len(failures)} of {len(budgeted)} sections outside "
              f"{FLOOR:.0%}-{CEILING:.0%} of budget")
        return 1
    print(f"PASS — all {len(budgeted)} sections within "
          f"{FLOOR:.0%}-{CEILING:.0%} of budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
