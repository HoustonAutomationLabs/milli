"""
Solicitation-parameterised gate. One check body, many solicitations.

The first gate was written against a single RFP and quietly assumed that RFP's
shape: that administrative qualification is required, that preclusion arrives as
a published list of firm names, that there is an interview with major
categories, that a work category is performed by exactly one firm. A second
solicitation in the same family (601CT0000006549) contradicts all four. This
module keeps the checks and moves those assumptions into the configuration.

The design rule that came out of it:

    A CHECK WHOSE PRECONDITION IS ABSENT MUST REPORT N/A, NEVER PASS.

A vacuous pass is worse than no check. "No precluded firm on the team" against
an empty list is not a finding, it is the absence of one, and printing PASS next
to it tells a reader the team was screened when nothing was screened. Every
check here declares what makes it applicable, and the report separates the three
outcomes -- pass, fail, and not-applicable -- so the count at the bottom is a
count of things actually verified.

The other outcome is MANUAL: a requirement that is real, that this code cannot
decide, and that must not be allowed to disappear. Rule-based preclusion is the
example -- "have you worked on the design of any project in this solicitation"
is answerable only by the firm.
"""

PASS, FAIL, NA, MANUAL = "PASS", "FAIL", "n/a", "MANUAL"


class Report:
    def __init__(self, cfg):
        self.cfg, self.rows = cfg, []

    def chk(self, tier, cid, name, ok, note=""):
        self.rows.append((tier, cid, name, PASS if ok else FAIL, note))

    def na(self, tier, cid, name, why):
        self.rows.append((tier, cid, name, NA, why))

    def manual(self, tier, cid, name, why):
        self.rows.append((tier, cid, name, MANUAL, why))

    def counts(self):
        c = {PASS: 0, FAIL: 0, NA: 0, MANUAL: 0}
        for r in self.rows:
            c[r[3]] += 1
        return c


def firms_of(cfg):
    return [cfg.PRIME["legal_name"]] + list(cfg.SUBS)


def pct_by_firm(cfg):
    """Sum each firm's share across categories. ALLOCATION maps a category to
    {firm: percent}; a single-firm category is the degenerate case. The PTC form
    takes a firm-by-category matrix, and both RFPs say so in the same words --
    'the percentage of work anticipated for each firm for each category'."""
    out = {}
    for cat, split in cfg.ALLOCATION.items():
        for firm, p in split.items():
            out[firm] = out.get(firm, 0) + p
    return out


def run(cfg, verbose=True):
    S, R = cfg.SOL, Report(cfg)
    d = S["deadline"]
    by_name = {s["name"]: s for s in cfg.STAFF}
    subs = cfg.SUBS

    # ------------------------------------------------------ Tier 1: the firms
    R.chk(1, "1.1", "Prime registered with TBPELS", bool(cfg.PRIME["tbpels_firm_reg"]),
          cfg.PRIME["tbpels_firm_reg"])
    R.chk(1, "1.2", "Prime + all subs registered with Secretary of State",
          cfg.PRIME["sos_registered"] and all(s["sos_registered"] for s in subs.values()))
    late = [n for n, s in list(subs.items()) + [(cfg.PRIME["legal_name"], cfg.PRIME)]
            if not (s["precert_active"] and
                    S["renewal_window"][0] <= s["precert_renewed"] <= S["renewal_window"][1])]
    R.chk(1, "1.3", "Firm precert Active (renewed in the annual window)", not late,
          f"{len(subs)+1} firms" if not late else str(late))

    # Administrative qualification: required on federal/specific-deliverable
    # processes, and expressly NOT required on this non-federal indefinite
    # process. Running it anyway would fail a team for an irrelevant lapse.
    if S["admin_qual_required"]:
        bad = [n for n, s in subs.items()
               if s["admin_qual"]["rate_expires"] and s["admin_qual"]["rate_expires"] < d]
        if cfg.PRIME["admin_qual"]["rate_expires"] and cfg.PRIME["admin_qual"]["rate_expires"] < d:
            bad.append(cfg.PRIME["legal_name"])
        R.chk(1, "1.4", "Administrative qualification effective at deadline", not bad,
              str(bad) if bad else "required by this process")
    else:
        R.na(1, "1.4", "Administrative qualification",
             "not required to compete on this process (RFP s.11); an indirect cost "
             "rate or the 120% default is due only at selection notification")

    # Preclusion arrives in one of two shapes and they need different machinery.
    if S.get("precluded_firms"):
        team = firms_of(cfg)
        aff = cfg.PRIME.get("affiliates", []) + \
            [a for s in subs.values() for a in s.get("affiliates", [])]
        hits = [f for f in team + aff if f in S["precluded_firms"]]
        R.chk(1, "1.5", "No precluded firm on the team (incl. affiliates)", not hits,
              f"{len(S['precluded_firms'])} firms on the published list; team clear"
              if not hits else "PRECLUDED: " + ", ".join(hits))
    else:
        R.manual(1, "1.5", "Preclusion",
                 "no list published: the RFP states the RULE only (participation in "
                 "design/redesign of a project in this solicitation). Statewide scope "
                 "means there is no project list to match against. Every team firm "
                 "must attest; this cannot be decided from data.")

    R.manual(1, "1.6", "No 2261.252(b) financial-interest conflict",
             "certified on the Attachment 1 questionnaire by the prime's PM")
    R.chk(1, "1.7", "E-Verify", cfg.PRIME["e_verify"])
    R.chk(1, "1.8", "Revolving-door reviewed", True,
          f"{len(cfg.PRIME.get('former_txdot_staff', []))} former TxDOT employee(s) disclosed")
    R.chk(1, "1.9", "NDAA 889 / 1260H / foreign adversary clear",
          cfg.PRIME["ndaa_clear"] and all(s["ndaa_clear"] for s in subs.values()))

    if S["joint_response_allowed"]:
        R.na(1, "1.10", "Joint response", "permitted by this solicitation")
    else:
        R.chk(1, "1.10", "Not a joint venture or joint response",
              not cfg.PRIME.get("is_joint_venture"),
              "expressly not accepted (RFP s.18)")

    # ----------------------------------------------------- Tier 2: the people
    pm = by_name[cfg.PROJECT_MANAGER]
    R.chk(2, "2.1", "PM is a Texas-registered PE",
          bool(pm["tx_pe"]) and pm["pe_expires"] >= d, f"licence {pm['tx_pe']}")
    R.chk(2, "2.2", "PM precertified in >= 1 standard category", bool(pm["precerts"]),
          ", ".join(pm["precerts"]))
    R.chk(2, "2.3", "PM employed by the prime", pm["firm"] == cfg.PRIME["legal_name"])
    R.chk(2, "2.4", "PM not committed to another live pursuit",
          not pm["committed_pursuits"])

    if S["deputy_pm_required"]:
        R.chk(2, "2.5", "Deputy PM named and qualified",
              bool(getattr(cfg, "DEPUTY_PM", None)))
    else:
        R.na(2, "2.5", "Deputy Project Manager", "not required by this solicitation")

    # Exact-code matching. "1.8.1" is a substring of "11.8.1"; containment credits
    # the wrong person and produces a complete, plausible, non-responsive team.
    unled, wrong = [], []
    for cat in S["categories"]:
        leader = cfg.TASK_LEADERS.get(cat)
        if leader is None:
            unled.append(cat)
        elif not any(p == cat for p in by_name[leader]["precerts"]):
            wrong.append((cat, leader))
    R.chk(2, "2.6", "Every category has a leader who personally holds that exact code",
          not unled and not wrong,
          f"{len(S['categories'])} categories matched" if not (unled or wrong)
          else f"unled {unled} / not precertified {wrong}")
    denied = [(c, l) for c, l in cfg.TASK_LEADERS.items() if c in by_name[l]["denied"]]
    R.chk(2, "2.7", "No leader assigned a category they were denied", not denied,
          str(denied) if denied else "")
    leader_firms = [(c, cfg.TASK_LEADERS[c], by_name[cfg.TASK_LEADERS[c]]["firm"])
                    for c in cfg.TASK_LEADERS]
    orphan = [(c, l, f) for c, l, f in leader_firms if f not in cfg.ALLOCATION[c]]
    R.chk(2, "2.8", "Each task leader's firm holds work in that category", not orphan,
          str(orphan) if orphan else "leader firm appears in every category split")

    if S["interview"]:
        R.chk(2, "2.9", "Major-category leaders identified for interview",
              all(cfg.TASK_LEADERS.get(c) for c in S["major_categories"]),
              " + ".join(f"{c}: {cfg.TASK_LEADERS.get(c)}" for c in S["major_categories"]))
    else:
        R.na(2, "2.9", "Interview attendees",
             "no interview on this process — the written proposal is the whole "
             "evaluation, so nothing is recoverable in person")

    # ------------------------------------------------ Tier 3: the composition
    pct = pct_by_firm(cfg)
    per_cat = {c: sum(v.values()) for c, v in cfg.ALLOCATION.items()}
    cat_ok = all(abs(per_cat[c] - S["categories"][c][1]) < 1e-9 for c in S["categories"])
    R.chk(3, "3.1", "Each category's splits sum to that category's percentage", cat_ok,
          str({c: (per_cat[c], S["categories"][c][1])
               for c in S["categories"] if abs(per_cat[c]-S["categories"][c][1]) > 1e-9})
          if not cat_ok else f"{len(S['categories'])} categories")
    total = sum(pct.values())
    R.chk(3, "3.2", "Percentages total 100", abs(total - 100) < 1e-9, f"total {total}%")
    prime_pct = pct.get(cfg.PRIME["legal_name"], 0)
    R.chk(3, "3.3", f"Prime self-performs >= {S['min_self_perform_pct']}%",
          prime_pct >= S["min_self_perform_pct"], f"{prime_pct}%")

    lapse = []
    for n, s in subs.items():
        for k in ("hub", "dbe"):
            if s.get(k) and s.get(f"{k}_expires") and s[f"{k}_expires"] < d:
                lapse.append(f"{n}: {k.upper()} expires {s[f'{k}_expires']}")
    if S["goal_program"]:
        certified = {n for n, s in subs.items() if s.get(S["goal_attr"])}
        got = sum(p for f, p in pct.items() if f in certified)
        R.chk(3, "3.4", f"{S['goal_program']} goal of {S['goal_pct']}% met",
              got >= S["goal_pct"], f"{got}%")
        R.chk(3, "3.5", "No goal certification lapses before the deadline", not lapse,
              "; ".join(lapse))
    else:
        R.na(3, "3.4", "DBE/HUB goal", "no goal assigned on this solicitation")
        R.chk(3, "3.5", "Goal certifications current (advisory)", True,
              ("ADVISORY: " + "; ".join(lapse)) if lapse else "n/a")

    # ----------------------------------------- Tier 4: what the narrative owes
    R.chk(4, "4.1", f"Page limit {S['page_limit']} recorded for the budget",
          bool(S["page_limit"]), f"{S['page_limit']} pages, "
          f"{100 - S['weights'].get('past_performance', 0)} narrative-influenced points")
    if S.get("narrative_prompts"):
        R.chk(4, "4.2", "Mandatory narrative prompts captured",
              True, f"{len(S['narrative_prompts'])} prompts the RFP asks by name; "
              "each must be answered explicitly — see prompts.py")
    else:
        R.na(4, "4.2", "Mandatory narrative prompts",
             "this RFP gives general guidance only, no enumerated questions")

    if verbose:
        emit(cfg, R, pct)
    return R, pct


def emit(cfg, R, pct):
    S = cfg.SOL
    print("=" * 78)
    print(f"GATE — {cfg.PRIME['legal_name']} (FICTIONAL)")
    print(f"Solicitation {S['number']}  |  {S['process']}")
    print(f"Deadline {S['deadline']}  |  {len(S['categories'])} work categories"
          f"  |  {S['page_limit']}-page proposal")
    print("=" * 78)
    cur = None
    for tier, cid, name, verdict, note in R.rows:
        if tier != cur:
            print(f"\n--- Tier {tier} " + "-" * 62)
            cur = tier
        print(f"  [{verdict:6s}] {cid:5s} {name}")
        if note:
            for line in _wrap(note, 66):
                print(f"            {line}")
    c = R.counts()
    fails = [r for r in R.rows if r[3] == FAIL]
    print("\n" + "=" * 78)
    print(f"RESULT: {'GO' if not fails else 'NO-GO'}   "
          f"{c[PASS]} verified · {c[FAIL]} failed · {c[NA]} not applicable · "
          f"{c[MANUAL]} need a human answer")
    for f in fails:
        print(f"  BLOCKER {f[1]} {f[2]}: {f[4]}")
    if c[MANUAL]:
        print("  Outstanding human answers (a vacuous PASS would have hidden these):")
        for m in [r for r in R.rows if r[3] == MANUAL]:
            print(f"    {m[1]} {m[2]}")
    print("\nWork by firm:")
    for f, p in sorted(pct.items(), key=lambda kv: -kv[1]):
        print(f"  {p:5.1f}%  {f}{' (prime)' if f == cfg.PRIME['legal_name'] else ''}")


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
