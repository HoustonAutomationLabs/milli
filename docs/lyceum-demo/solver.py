"""
Team-composition solver: can this firm library cover this solicitation, and how?

The gate answers "is this proposed team allowed to bid". It takes the allocation
as an input. This answers the question that comes first and that firms actually
get wrong: given the people we have, IS there an allocation that satisfies every
constraint at once, and if not, what exactly is missing?

The constraints pull against each other:

  * every work category needs a firm AND a named individual precertified in that
    exact category;
  * the prime must self-perform at least a stated share of the work;
  * where a goal programme applies, certified firms must hold at least the goal
    share -- which is the prime's floor pushing up and the goal floor pushing
    down on the same 100 points;
  * percentages must total exactly 100;
  * no precluded firm, and no affiliate of one.

A firm that assembles a team by instinct discovers an infeasibility after it has
asked six subproviders for letters. This reports it in a second, and reports the
specific gap rather than "no solution".

Category codes are matched by EXACT EQUALITY, never containment. This
solicitation requires both 1.8.1 and 11.8.1; a substring matcher credits the
scheduling lead with public involvement and puts 5% of the work under someone
who is not precertified to lead it.

Run: python3 solver.py
"""
from gate import SOL, PRIME, SUBS, STAFF, PROJECT_MANAGER

MIN_PRIME = SOL["min_self_perform_pct"]
CATS = SOL["categories"]

# JUDGEMENT PARAMETERS, not solicitation requirements. The solicitation states no
# limit on how much work one individual may lead, and the first version of this
# solver exploited that: it satisfied every stated constraint and handed the
# Project Manager three task-leader roles covering 35% of the work on top of
# managing the contract. Nothing in the rules forbids it, and no evaluator would
# score it well -- key-staff experience is 26 points and project planning 30, and
# both are read as questions about depth. So the cap is here, marked for what it
# is: a defensible default the client can move, not a rule from the document.
MAX_LEADER_SHARE = 25      # no one individual leads more than this share
PM_LEADS_CATEGORIES = False # the PM is not also a task leader if avoidable


def qualified(code, staff=STAFF, firms=None):
    """Individuals who may LEAD this exact category. Pending is not qualified --
    a precertification under review is not a precertification -- and denied is a
    standing bar, not a silence."""
    out = []
    for s in staff:
        if firms is not None and s["firm"] not in firms:
            continue
        if code in s["denied"] or code in s["pending"]:
            continue
        if any(p == code for p in s["precerts"]):        # exact, never `in`
            out.append(s)
    return out


def available_firms():
    """Firm library minus anyone barred. Affiliates of a precluded firm are
    barred with it."""
    barred, reasons = set(), {}
    for name, f in [(PRIME["legal_name"], PRIME)] + list(SUBS.items()):
        if name in SOL["precluded_firms"]:
            barred.add(name); reasons[name] = "named on the preclusion list"
        for a in f.get("affiliates", []):
            if a in SOL["precluded_firms"]:
                barred.add(name); reasons[name] = f"affiliate {a} is precluded"
    firms = [n for n, _ in [(PRIME["legal_name"], PRIME)] + list(SUBS.items())
             if n not in barred]
    return firms, reasons


def coverage(firms):
    """Per category: who can lead it. Zero is a blocker; one is a risk."""
    return {c: qualified(c, firms=set(firms)) for c in CATS}


def solve(firms, goal_pct=0, goal_attr="dbe"):
    """Assign every category to a firm and a leader, meeting both floors.

    Small enough to solve by ordering rather than search: assign each category to
    the candidate that most helps whichever floor is furthest from being met.
    Then verify -- a heuristic that reports success without verifying is worse
    than no solver at all."""
    cov = coverage(firms)
    unassignable = [c for c, who in cov.items() if not who]
    if unassignable:
        return None, unassignable, {}

    certified = {n for n, f in SUBS.items() if f.get(goal_attr)}
    prime = PRIME["legal_name"]
    alloc, prime_pct, goal_got = {}, 0.0, 0.0
    load = {}                                  # individual -> share led so far
    pm = PROJECT_MANAGER

    # Hardest first: a category with one candidate has no choice to trade away.
    order = sorted(CATS, key=lambda c: (len(cov[c]), -CATS[c][1]))
    for c in order:
        pct = CATS[c][1]
        cands = cov[c]
        def score(s):
            f, who = s["firm"], s["name"]
            gain = 0
            if load.get(who, 0) + pct > MAX_LEADER_SHARE:
                gain -= 4                      # concentration: last resort only
            if who == pm and not PM_LEADS_CATEGORIES:
                gain -= 3                      # PM manages; someone else leads
            if f == prime and prime_pct < MIN_PRIME:
                gain += 2                      # prime floor unmet: prefer prime
            if f in certified and goal_got < goal_pct:
                gain += 2                      # goal unmet: prefer certified
            if f == prime and prime_pct >= MIN_PRIME and goal_got >= goal_pct:
                gain += 1                      # both met: keep work in-house
            return (gain, s["years"])
        pick = max(cands, key=score)
        alloc[c] = (pick["firm"], pick["name"])
        if pick["firm"] == prime:
            prime_pct += pct
        if pick["firm"] in certified:
            goal_got += pct
        load[pick["name"]] = load.get(pick["name"], 0) + pct

    return alloc, [], {"prime_pct": prime_pct, "goal_pct": goal_got}


def verify(alloc, goal_pct=0, goal_attr="dbe"):
    """Independent check of the solver's own output."""
    prime = PRIME["legal_name"]
    certified = {n for n, f in SUBS.items() if f.get(goal_attr)}
    total = sum(CATS[c][1] for c in alloc)
    prime_pct = sum(CATS[c][1] for c, (f, _) in alloc.items() if f == prime)
    goal_got = sum(CATS[c][1] for c, (f, _) in alloc.items() if f in certified)
    bad_leader = [c for c, (f, ldr) in alloc.items()
                  if not any(s["name"] == ldr and s["firm"] == f
                             and c in s["precerts"] and c not in s["denied"]
                             and c not in s["pending"] for s in STAFF)]
    load = {}
    for c, (_, ldr) in alloc.items():
        load[ldr] = load.get(ldr, 0) + CATS[c][1]
    heavy = {k: v for k, v in load.items() if v > MAX_LEADER_SHARE}
    pm_leads = [c for c, (_, ldr) in alloc.items() if ldr == PROJECT_MANAGER]
    return [
        ("percentages total exactly 100", total == 100, f"{total}"),
        (f"prime self-performs >= {MIN_PRIME}%", prime_pct >= MIN_PRIME,
         f"{prime_pct:.0f}%"),
        (f"goal share >= {goal_pct}%", goal_got >= goal_pct,
         f"{goal_got:.0f}%" + (" (no goal assigned)" if not goal_pct else "")),
        ("every leader precertified in the exact category", not bad_leader,
         str(bad_leader) if bad_leader else f"{len(alloc)} categories"),
        (f"no individual leads more than {MAX_LEADER_SHARE}% (judgement)",
         not heavy, str(heavy) if heavy else
         f"heaviest {max(load.values())}% ({len(load)} leaders)"),
        ("PM not also a task leader (judgement)", not pm_leads,
         str(sorted(pm_leads)) if pm_leads else PROJECT_MANAGER),
    ]


def report(label, firms, goal_pct=0, note=""):
    print("=" * 78)
    print(f"SCENARIO — {label}")
    if note:
        print(f"  {note}")
    print("=" * 78)
    cov = coverage(firms)
    gaps = [c for c, w in cov.items() if not w]
    solo = [c for c, w in cov.items() if len(w) == 1]

    if gaps:
        print("  NO FEASIBLE TEAM. Categories nobody in the library can lead:")
        for c in sorted(gaps):
            n, pct = CATS[c]
            print(f"    {c:<9} {n:<44} {pct:>2}% of the work")
        print("  Fix: precertify a current employee in these codes, or add a")
        print("  subprovider that holds them. Both take longer than the window.")
        print()
        return

    alloc, _, stats = solve(firms, goal_pct)
    checks = verify(alloc, goal_pct)
    ok = all(c[1] for c in checks)
    print(f"  {'PASS' if ok else 'FAIL'} — feasible allocation "
          f"over {len(set(f for f, _ in alloc.values()))} firms")
    for name, good, note_ in checks:
        print(f"    [{'ok' if good else 'XX'}] {name:<48} {note_}")
    if solo:
        print(f"  Single point of failure — {len(solo)} categories have exactly one")
        print("  qualified leader in the whole library. Losing that person or that")
        print("  firm makes the bid infeasible, not merely weaker:")
        for c in sorted(solo, key=lambda x: -CATS[x][1])[:6]:
            who = cov[c][0]
            print(f"    {c:<9} {CATS[c][0][:38]:<40} only {who['name']}")
        if len(solo) > 6:
            print(f"    ... and {len(solo)-6} more")
    print()


def goal_ceiling(firms, goal_attr="dbe"):
    """The largest goal share this library could meet even at its best: for each
    category, is ANY qualified leader at a certified firm? A goal above this
    number is unreachable no matter how the work is arranged -- which is a
    go/no-go answer, not a staffing preference."""
    certified = {n for n, f in SUBS.items() if f.get(goal_attr)}
    reachable = 0
    for c, (_, pct) in CATS.items():
        if any(s["firm"] in certified for s in qualified(c, firms=set(firms))):
            reachable += pct
    return reachable, certified


def single_firm_sensitivity(firms):
    """Which single subprovider, if lost, makes the bid infeasible? A firm can
    walk away, get acquired, or land on a preclusion list between the shortlist
    and the deadline. This says which departures are survivable."""
    out = []
    for f in firms:
        if f == PRIME["legal_name"]:
            continue
        rest = [x for x in firms if x != f]
        gaps = [c for c, who in coverage(rest).items() if not who]
        out.append((f, gaps, sum(CATS[c][1] for c in gaps)))
    return out


if __name__ == "__main__":
    firms, barred = available_firms()
    report("as-is, this solicitation (no goal assigned)", firms,
           goal_pct=0,
           note=f"{len(firms)} firms available, {len(barred)} barred")

    # What a goal does to the same library. Federal solicitations in this family
    # do carry DBE goals; this one happens not to. The interesting number is not
    # whether a given goal is met but the highest goal the library could ever
    # meet -- above that the answer is "do not bid", weeks earlier than a firm
    # would otherwise find out.
    ceiling, certified = goal_ceiling(firms)
    print("=" * 78)
    print("GOAL CEILING — the highest DBE share this library could ever reach")
    print("=" * 78)
    print(f"  {len(certified)} certified firms in the library: "
          f"{', '.join(sorted(certified))}")
    print(f"  categories they can lead account for {ceiling}% of the work")
    print(f"  a goal at or under {ceiling}% is reachable; above it, no arrangement")
    print(f"  of this library qualifies and the answer is do-not-bid")
    print()
    report(f"DBE goal at the ceiling ({ceiling}%)", firms, goal_pct=ceiling,
           note="binding: every certified-firm category must be assigned to one")

    print("=" * 78)
    print("SINGLE-FIRM SENSITIVITY — which departure kills the bid")
    print("=" * 78)
    print("  A subprovider can walk, be acquired, or land on a preclusion list")
    print("  after the team is assembled. Preclusion is the live risk here: this")
    print("  solicitation bars seven named firms, and 4.5.1 Constructability")
    print("  Review is required work -- the specialists most likely to hold it")
    print("  are the ones most likely to have done the design contract.")
    for f, gaps, pct in sorted(single_firm_sensitivity(firms),
                               key=lambda x: -x[2]):
        if gaps:
            print(f"    FATAL   losing {f}")
            plural = "category" if len(gaps) == 1 else "categories"
            print(f"            leaves {len(gaps)} {plural} unleadable, {pct}% of the work")
        else:
            print(f"    survivable  losing {f}")
    print("=" * 78)

    # ---------------------------------------------------------------- regression
    # The failure mode that produces a wrong team rather than no team. This
    # solicitation requires 1.8.1 Public Involvement and 11.8.1 Construction
    # Schedule Support - Bridges. "1.8.1" is a substring of "11.8.1", so a
    # containment matcher reports the scheduling lead as qualified to lead public
    # involvement. Nothing downstream catches it: the allocation is complete, the
    # percentages total 100, and 5% of the work sits under someone who cannot
    # lead it. Kept as a running test because it is invisible by inspection.
    print()
    print("=" * 78)
    print("REGRESSION — exact-code matching vs. containment")
    print("=" * 78)
    buggy = [s for s in STAFF if any(c in "".join(s["precerts"]) for c in ["1.8.1"])
             and "1.8.1" not in s["precerts"]]
    strict = [s["name"] for s in qualified("1.8.1")]
    print(f"  1.8.1 Public Involvement, {CATS['1.8.1'][1]}% of the work")
    print(f"    exact match  -> {strict}")
    print(f"    containment  -> would ALSO credit {[s['name'] for s in buggy]}")
    print(f"                    (they hold 11.8.1, which contains the string 1.8.1)")
    ok = bool(buggy) and not any(s["name"] in strict for s in buggy)
    print(f"  [{'PASS' if ok else 'FAIL'}] collision present in this solicitation "
          f"and the exact matcher rejects it")
    print("=" * 78)
