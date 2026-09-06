"""
Prompt coverage: did the narrative answer every question the RFP asked by name?

601CT0000006541 gave general guidance -- discuss your technical approach, your
PM's experience -- and a proposal could address it in any order and any words.
601CT0000006549 does something different: it asks FOUR specific questions, three
of which demand a worked example ("include one example of a bridge inspection
where your team identified a critical finding"). That is machine-checkable in a
way general guidance is not, and it is the most expensive thing to get wrong,
because an unanswered named question is a scoring zero on a criterion rather
than a weak paragraph.

Two things are checked and they fail differently:

  COVERAGE  every term the question is built around appears in the narrative.
            Missing "scour" entirely is not a stylistic problem.
  EXAMPLE   a question that says "include one example" needs a concrete
            instance, not a claim of capability. The heuristic looks for a
            narrative marker near the topic; it can be fooled by a firm that
            writes "for example, we are very experienced", so it reports what
            it matched and a human confirms. A check that can be fooled must
            say so rather than print a bare PASS.

Run: python3 prompts.py <config-module> <narrative.md>
"""
import re, sys, importlib


def coverage(cfg, text):
    lo = text.lower()
    rows = []
    for p in cfg.SOL.get("narrative_prompts") or []:
        missing = [t for t in p["must_mention"] if t.lower() not in lo]
        ex = None
        if p["needs_example"]:
            topic = p["must_mention"][0].lower()
            # a worked example: an example marker within ~600 chars of the topic
            ex = False
            for m in re.finditer(re.escape(topic), lo):
                w = lo[max(0, m.start() - 600): m.start() + 600]
                if re.search(r'\b(for example|one example|in 20\d\d|on the |'
                             r'we identified|our team identified|case:)\b', w):
                    ex = True
                    break
        rows.append((p, missing, ex))
    return rows


def main(cfgname, path):
    cfg = importlib.import_module(cfgname)
    text = open(path).read()
    rows = coverage(cfg, text)
    if not rows:
        print(f"{cfg.SOL['number']}: no enumerated narrative prompts — n/a")
        return 0

    print("=" * 78)
    print(f"PROMPT COVERAGE — {cfg.SOL['number']}")
    print("=" * 78)
    bad = 0
    for p, missing, ex in rows:
        ok = not missing and (ex is not False)
        bad += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {p['id']}  ({p['criterion']}, "
              f"weight {cfg.SOL['weights'][p['criterion']]})")
        print(f"        {p['ask'][:74]}")
        for line in _wrap(p['ask'][74:], 74):
            print(f"        {line}")
        if missing:
            print(f"        MISSING TERMS: {missing}")
        if p["needs_example"]:
            print(f"        worked example: "
                  f"{'found near the topic' if ex else 'NOT FOUND — the RFP says include one'}")
    print("=" * 78)
    print(f"{len(rows)-bad} of {len(rows)} named questions answered"
          + ("" if not bad else f" — {bad} INCOMPLETE"))
    print("Example detection is a heuristic and can be satisfied by a vague "
          "sentence; confirm each by eye before submitting.")
    return 1 if bad else 0


def _wrap(s, w):
    words, line, out = s.split(), "", []
    for x in words:
        if len(line) + len(x) + 1 > w:
            out.append(line); line = x
        else:
            line = f"{line} {x}".strip()
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
