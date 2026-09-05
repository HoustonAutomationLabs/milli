"""
End-to-end gate run: fictional firm against TxDOT solicitation 601CT0000006541.

ALL FIRM AND PERSONNEL DATA IN THIS FILE IS FICTIONAL. Precluded-firm names are
the real ones published in TxDOT's own preclusion document for this solicitation
(a public list of firms barred from bidding); they appear only as data the gate
tests against, and none of them is represented as bidding.

Run: python3 gate.py
"""
from datetime import date

# ---------------------------------------------------------------- solicitation
SOL = {
    "number": "601CT0000006541",
    "legacy": "14-7SDP5003",
    "posted": date(2026, 9, 1),
    "questions_close": date(2026, 9, 8),
    "deadline": date(2026, 9, 22),          # 1:00 p.m. CT
    "process": "RFP / specific deliverable / federal / with interview",
    "goal_program": None,                    # federal, but NO DBE goal assigned
    "goal_pct": 0,
    "min_self_perform_pct": 30,
    "admin_qual_required": True,
    "preclusion_declared": True,
    "page_limit": 12,
    "major_categories": ["11.2.1", "11.3.1"],   # must attend interview
    "interview_extra_task_leaders": 1,
    "categories": {
        "1.8.1": ("Public Involvement", 5), "4.5.1": ("Constructability Review", 1),
        "11.1.1": ("Roadway Construction Mgmt & Inspection", 10),
        "11.2.1": ("Bridge Construction Mgmt & Inspection", 20),
        "11.3.1": ("Construction Superintendent", 17),
        "11.4.1": ("Environmental Inspections", 3),
        "11.5.1": ("Construction Scheduling Project Manager", 1),
        "11.6.1": ("Construction Schedule Support - General", 2),
        "11.8.1": ("Construction Schedule Support - Bridges/Interchanges", 4),
        "11.10.1": ("Construction Record Keeper", 8),
        "12.1.1": ("Asphaltic Concrete Production", 1),
        "12.1.2": ("Portland Cement Concrete", 1), "12.1.3": ("Materials Engineering", 1),
        "12.1.4": ("Asphaltic Concrete Placement", 4),
        "12.1.5": ("Portland Cement Concrete Placement", 3),
        "12.1.6": ("Embankment/Subgrade/Backfill/Base Production", 2),
        "12.1.7": ("Embankment/Subgrade/Backfill/Base Placement", 1),
        "12.2.1": ("Concrete Plant Inspection and Testing", 1),
        "12.2.5": ("HMA Plant Inspection and Testing", 1),
        "14.1.1": ("Soil Exploration", 1), "14.2.1": ("Geotechnical Testing", 1),
        "15.2.1": ("Design Survey", 1), "15.2.2": ("Construction Survey", 1),
        "15.3.5": ("Horizontal and Vertical Control", 1),
        "18.3.1": ("Utility Adjustment Coordination", 4),
        "18.5.1": ("Utility Construction Mgmt & Verification", 4),
        "23.8.1": ("Claims Analysis and Management", 1),
    },
    # verbatim from the published Preclusion Document for this solicitation
    "precluded_firms": [
        "STV Incorporated", "EDGE Engineering, PLLC",
        "Foresight Planning & Engineering Services, LLC", "HDR Engineering, Inc.",
        "IEA Inc.", "Lamb-Star Engineering, LLC", "Michael Baker International, Inc.",
    ],
}

# ------------------------------------------------------- fictional firm library
PRIME = {
    "legal_name": "Ocotillo Engineering Group, LLC",
    "dba": None,
    "tin": "17412900355",
    "ccis_seq": "00004417",
    "tbpels_firm_reg": "F-22841",
    "sos_registered": True,
    "precert_active": True,
    "precert_renewed": date(2026, 2, 17),      # inside 1 Jan - 31 Mar window
    "admin_qual": {"status": "Effective", "rate_expires": date(2027, 3, 31)},
    "dbe": False, "hub": False,
    "affiliates": ["Ocotillo Field Services, LLC"],
    "former_txdot_staff": [{"name": "R. Alvarez", "left": date(2022, 6, 30)}],
    "e_verify": True,
    "ndaa_clear": True,
    "design_work_on_project": False,
    "ps_cams_esa": None,                        # no history -> default applies
}

SUBS = {
    "Barton Creek Materials Testing, LLC": dict(
        precert_active=True, precert_renewed=date(2026, 3, 3), sos_registered=True,
        admin_qual={"status": "Effective", "rate_expires": date(2027, 5, 31)},
        dbe=True, dbe_naics=["541380"], dbe_expires=date(2027, 1, 15),
        hub=False, ndaa_clear=True, affiliates=[]),
    "Caliche Geotechnical, Inc.": dict(
        precert_active=True, precert_renewed=date(2026, 1, 22), sos_registered=True,
        admin_qual={"status": "Effective", "rate_expires": date(2027, 8, 31)},
        dbe=False, hub=False, ndaa_clear=True, affiliates=[]),
    "Pecan Bayou Survey Company": dict(
        precert_active=True, precert_renewed=date(2026, 3, 28), sos_registered=True,
        admin_qual={"status": "Safe harbor", "rate_expires": None},
        dbe=False, hub=True, hub_expires=date(2026, 9, 12),   # EXPIRES BEFORE DEADLINE
        ndaa_clear=True, affiliates=[]),
    "Windrow Public Affairs, LLC": dict(
        precert_active=True, precert_renewed=date(2026, 2, 9), sos_registered=True,
        admin_qual={"status": "Exempt (non-engineering)", "rate_expires": None},
        dbe=True, dbe_naics=["541820"], dbe_expires=date(2028, 4, 1),
        hub=True, hub_expires=date(2028, 4, 1), ndaa_clear=True, affiliates=[]),
    "Llano Utility Coordination, LLC": dict(
        precert_active=True, precert_renewed=date(2026, 3, 11), sos_registered=True,
        admin_qual={"status": "Effective", "rate_expires": date(2027, 2, 28)},
        dbe=False, hub=False, ndaa_clear=True, affiliates=[]),
    "Blanco Environmental Services, LLC": dict(
        precert_active=True, precert_renewed=date(2026, 2, 25), sos_registered=True,
        admin_qual={"status": "Effective", "rate_expires": date(2027, 6, 30)},
        dbe=False, hub=False, ndaa_clear=True, affiliates=[]),
}

# staff: precerts stored as LISTS OF CODES, never as text
STAFF = [
    dict(name="Marisol Everly, P.E.", firm="Ocotillo Engineering Group, LLC",
         ccis_emp_seq="000031882", tx_pe="118432", pe_expires=date(2027, 12, 31),
         precerts=["11.1.1", "11.2.1", "11.3.1", "11.10.1"], denied=[], pending=[],
         years=19, role="Project Manager", committed_pursuits=[]),
    dict(name="Dov Ranganathan, P.E.", firm="Ocotillo Engineering Group, LLC",
         ccis_emp_seq="000029104", tx_pe="104778", pe_expires=date(2027, 12, 31),
         precerts=["11.2.1", "11.8.1", "4.5.1"], denied=["11.6.1"], pending=[],
         years=22, role="Bridge CM&I Task Leader", committed_pursuits=[]),
    dict(name="Thea Kowalczyk", firm="Ocotillo Engineering Group, LLC",
         ccis_emp_seq="000033507", tx_pe=None, pe_expires=None,
         precerts=["11.3.1", "11.10.1"], denied=[], pending=[], years=15,
         role="Construction Superintendent Task Leader", committed_pursuits=[]),
    dict(name="Ike Brannigan, P.E.", firm="Ocotillo Engineering Group, LLC",
         ccis_emp_seq="000030266", tx_pe="121905", pe_expires=date(2027, 12, 31),
         precerts=["11.5.1", "11.6.1", "11.8.1", "23.8.1"], denied=[], pending=[],
         years=17, role="Scheduling / Claims Task Leader", committed_pursuits=[]),
    dict(name="Priya Vasquez-Lund, P.E.", firm="Ocotillo Engineering Group, LLC",
         ccis_emp_seq="000034991", tx_pe="129440", pe_expires=date(2027, 12, 31),
         precerts=["11.1.1", "11.10.1"], denied=[], pending=["11.4.1"], years=11,
         role="Roadway CM&I Task Leader", committed_pursuits=[]),
    dict(name="Corbin Ashworth", firm="Barton Creek Materials Testing, LLC",
         ccis_emp_seq="000027713", tx_pe=None, pe_expires=None,
         precerts=["12.1.1","12.1.2","12.1.3","12.1.4","12.1.5","12.1.6","12.1.7",
                   "12.2.1","12.2.5"], denied=[], pending=[], years=21,
         role="Materials Task Leader", committed_pursuits=[]),
    dict(name="Halvard Nkemelu, P.E.", firm="Caliche Geotechnical, Inc.",
         ccis_emp_seq="000028450", tx_pe="099317", pe_expires=date(2027, 12, 31),
         precerts=["14.1.1", "14.2.1"], denied=[], pending=[], years=24,
         role="Geotechnical Task Leader", committed_pursuits=[]),
    dict(name="Rosalind Tejeda, R.P.L.S.", firm="Pecan Bayou Survey Company",
         ccis_emp_seq="000031045", tx_pe=None, rpls="6284", pe_expires=None,
         precerts=["15.2.1", "15.2.2", "15.3.5"], denied=[], pending=[], years=18,
         role="Survey Task Leader", committed_pursuits=[]),
    dict(name="Junnosuke Abelard", firm="Windrow Public Affairs, LLC",
         ccis_emp_seq="000035778", tx_pe=None, pe_expires=None,
         precerts=["1.8.1"], denied=[], pending=[], years=13,
         role="Public Involvement Task Leader", committed_pursuits=[]),
    dict(name="Ottoline Kirkbride, P.E.", firm="Llano Utility Coordination, LLC",
         ccis_emp_seq="000032319", tx_pe="113806", pe_expires=date(2027, 12, 31),
         precerts=["18.3.1", "18.5.1"], denied=[], pending=[], years=16,
         role="Utility Task Leader", committed_pursuits=[]),
    dict(name="Ferris Onwuachi, P.E.", firm="Blanco Environmental Services, LLC",
         ccis_emp_seq="000034120", tx_pe="126553", pe_expires=date(2027, 12, 31),
         precerts=["11.4.1"], denied=[], pending=[], years=12,
         role="Environmental Task Leader", committed_pursuits=[]),
]

# proposed allocation: category -> (firm, task leader)
ALLOCATION = {
    "11.1.1": ("Ocotillo Engineering Group, LLC", "Priya Vasquez-Lund, P.E."),
    "11.2.1": ("Ocotillo Engineering Group, LLC", "Dov Ranganathan, P.E."),
    "11.3.1": ("Ocotillo Engineering Group, LLC", "Thea Kowalczyk"),
    "11.10.1": ("Ocotillo Engineering Group, LLC", "Marisol Everly, P.E."),
    "11.5.1": ("Ocotillo Engineering Group, LLC", "Ike Brannigan, P.E."),
    "11.6.1": ("Ocotillo Engineering Group, LLC", "Ike Brannigan, P.E."),
    "11.8.1": ("Ocotillo Engineering Group, LLC", "Ike Brannigan, P.E."),
    "23.8.1": ("Ocotillo Engineering Group, LLC", "Ike Brannigan, P.E."),
    "4.5.1":  ("Ocotillo Engineering Group, LLC", "Dov Ranganathan, P.E."),
    "12.1.1": ("Barton Creek Materials Testing, LLC", "Corbin Ashworth"),
    "12.1.2": ("Barton Creek Materials Testing, LLC", "Corbin Ashworth"),
    "12.1.3": ("Barton Creek Materials Testing, LLC", "Corbin Ashworth"),
    "12.1.4": ("Barton Creek Materials Testing, LLC", "Corbin Ashworth"),
    "12.1.5": ("Barton Creek Materials Testing, LLC", "Corbin Ashworth"),
    "12.1.6": ("Barton Creek Materials Testing, LLC", "Corbin Ashworth"),
    "12.1.7": ("Barton Creek Materials Testing, LLC", "Corbin Ashworth"),
    "12.2.1": ("Barton Creek Materials Testing, LLC", "Corbin Ashworth"),
    "12.2.5": ("Barton Creek Materials Testing, LLC", "Corbin Ashworth"),
    "14.1.1": ("Caliche Geotechnical, Inc.", "Halvard Nkemelu, P.E."),
    "14.2.1": ("Caliche Geotechnical, Inc.", "Halvard Nkemelu, P.E."),
    "15.2.1": ("Pecan Bayou Survey Company", "Rosalind Tejeda, R.P.L.S."),
    "15.2.2": ("Pecan Bayou Survey Company", "Rosalind Tejeda, R.P.L.S."),
    "15.3.5": ("Pecan Bayou Survey Company", "Rosalind Tejeda, R.P.L.S."),
    "1.8.1":  ("Windrow Public Affairs, LLC", "Junnosuke Abelard"),
    "18.3.1": ("Llano Utility Coordination, LLC", "Ottoline Kirkbride, P.E."),
    "18.5.1": ("Llano Utility Coordination, LLC", "Ottoline Kirkbride, P.E."),
    "11.4.1": ("Blanco Environmental Services, LLC", "Ferris Onwuachi, P.E."),
}

PROJECT_MANAGER = "Marisol Everly, P.E."

# firms the prime contacted during teaming but did not put on the team
CONTACTED_NOT_TEAMED = [
    ("Sabine Valley Inspection Services, LLC", "roadway inspection surge"),
    ("Trinity Forks Testing Group, LLC", "materials testing"),
    ("Guadalupe Bend Constructability Advisors, LLC", "constructability review"),
]

# Separate logic test only -- NOT part of the fabricated submission. Exercises the
# preclusion check against the real published list without naming any real firm in
# a document that looks like a filed response.
def preclusion_selftest():
    hypothetical = ["Ocotillo Engineering Group, LLC"] + SOL["precluded_firms"][:1]
    hits = [f for f in hypothetical if f in SOL["precluded_firms"]]
    print("\n--- preclusion check self-test ---------------------------------------")
    print(f"  published list carries {len(SOL['precluded_firms'])} firms barred from this contract")
    print(f"  hypothetical team containing one of them -> {'CAUGHT' if hits else 'MISSED'}")
    print("  note: 4.5.1 Constructability Review is a required category here, and the")
    print("  firm that performed constructability review on the design contract is on")
    print("  the barred list. The obvious specialist is the one that disqualifies you.")

# ================================================================== the checks
def run():
    d = SOL["deadline"]; out = []
    def chk(tier, cid, name, ok, note=""):
        out.append((tier, cid, name, ok, note))

    by_name = {s["name"]: s for s in STAFF}

    # ---- Tier 1: firm eligibility as of the deadline
    chk(1, "1.1", "Prime registered with TBPELS", bool(PRIME["tbpels_firm_reg"]),
        PRIME["tbpels_firm_reg"])
    all_sos = PRIME["sos_registered"] and all(s["sos_registered"] for s in SUBS.values())
    chk(1, "1.2", "Prime + all subs registered with Secretary of State", all_sos)
    renew_ok = [n for n, s in list(SUBS.items()) + [(PRIME["legal_name"], PRIME)]
                if not (s["precert_active"] and
                        date(2026,1,1) <= s["precert_renewed"] <= date(2026,3,31))]
    chk(1, "1.3", "Firm precert Active (renewed 1 Jan - 31 Mar)", not renew_ok,
        "all 7 firms renewed in window" if not renew_ok else str(renew_ok))
    aq_bad = [n for n, s in SUBS.items()
              if s["admin_qual"]["rate_expires"] and s["admin_qual"]["rate_expires"] < d]
    aq_bad += ([PRIME["legal_name"]] if PRIME["admin_qual"]["rate_expires"] < d else [])
    chk(1, "1.4", "Administrative qualification effective at deadline", not aq_bad,
        "required: federal/specific-deliverable")
    team = [PRIME["legal_name"]] + list(SUBS)
    aff = PRIME["affiliates"] + [a for s in SUBS.values() for a in s.get("affiliates", [])]
    hits = [f for f in team + aff if f in SOL["precluded_firms"]]
    chk(1, "1.5", "No precluded firm on the team (incl. affiliates)", not hits,
        f"{len(SOL['precluded_firms'])} firms on published list; team clear" if not hits
        else "PRECLUDED: " + ", ".join(hits))
    chk(1, "1.6", "No 2261.252(b) financial-interest conflict", True, "attested")
    chk(1, "1.7", "E-Verify", PRIME["e_verify"])
    chk(1, "1.8", "Revolving-door reviewed", True,
        f"{len(PRIME['former_txdot_staff'])} former TxDOT employee(s) disclosed")
    chk(1, "1.9", "NDAA 889 / 1260H / foreign adversary clear",
        PRIME["ndaa_clear"] and all(s["ndaa_clear"] for s in SUBS.values()), "new in 2026")

    # ---- Tier 2: people as of the deadline
    pm = by_name[PROJECT_MANAGER]
    chk(2, "2.1", "PM is a Texas-registered PE", bool(pm["tx_pe"]) and pm["pe_expires"] >= d,
        f"licence {pm['tx_pe']}")
    chk(2, "2.2", "PM precertified in >=1 standard category", len(pm["precerts"]) > 0,
        ", ".join(pm["precerts"]))
    chk(2, "2.3", "PM employed by the prime", pm["firm"] == PRIME["legal_name"])
    chk(2, "2.4", "PM not named on another live pursuit", not pm["committed_pursuits"],
        "one interview only")
    missing = []
    for cat in SOL["categories"]:
        firm, leader = ALLOCATION.get(cat, (None, None))
        if leader is None or cat not in by_name[leader]["precerts"]:
            missing.append(cat)
    chk(2, "2.5", "Every category has a named leader who personally holds it",
        not missing, f"{len(SOL['categories'])} categories, all matched"
        if not missing else f"unmatched: {missing}")
    denied_hits = [(c, l) for c, (f, l) in ALLOCATION.items() if c in by_name[l]["denied"]]
    chk(2, "2.6", "No leader assigned a category they were denied", not denied_hits)
    maj_ok = all(ALLOCATION[c][1] for c in SOL["major_categories"])
    chk(2, "2.7", "Major-category leaders identified for interview", maj_ok,
        " + ".join(f"{c}: {ALLOCATION[c][1]}" for c in SOL["major_categories"]))

    # ---- Tier 3: composition
    pct = {}
    for cat, (firm, _) in ALLOCATION.items():
        pct[firm] = pct.get(firm, 0) + SOL["categories"][cat][1]
    total = sum(pct.values())
    chk(3, "3.1", "Category percentages total 100", total == 100, f"total {total}%")
    prime_pct = pct.get(PRIME["legal_name"], 0)
    chk(3, "3.2", f"Prime self-performs >= {SOL['min_self_perform_pct']}%",
        prime_pct >= SOL["min_self_perform_pct"], f"{prime_pct}%")
    chk(3, "3.3", "DBE/HUB goal met", True, "no goal assigned on this solicitation")
    lapse = []
    for n, s in SUBS.items():
        if s.get("hub") and s.get("hub_expires") and s["hub_expires"] < d:
            lapse.append(f"{n}: HUB expires {s['hub_expires']}")
        if s.get("dbe") and s.get("dbe_expires") and s["dbe_expires"] < d:
            lapse.append(f"{n}: DBE expires {s['dbe_expires']}")
    # 3.4 severity depends on whether a goal is assigned. With no goal programme a
    # lapsed DBE/HUB certificate cannot make the response non-responsive -- it is
    # still reported, because it is wrong on the Subprovider Info form and it will
    # block the same team on the next solicitation that does carry a goal.
    if SOL["goal_program"] is None:
        chk(3, "3.4", "Goal certifications current (advisory - no goal assigned)",
            True, ("ADVISORY: " + "; ".join(lapse)) if lapse else "n/a")
    else:
        chk(3, "3.4", "No goal certification lapses before the deadline", not lapse,
            "; ".join(lapse) if lapse else "")

    # ---- substring demonstration
    naive_ok = any("1.8.1" in p for p in by_name["Ike Brannigan, P.E."]["precerts"])
    strict_ok = "1.8.1" in by_name["Ike Brannigan, P.E."]["precerts"]

    # ---------------------------------------------------------------- report
    print("=" * 74)
    print(f"GATE RUN — {PRIME['legal_name']} (FICTIONAL)")
    print(f"Solicitation {SOL['number']} ({SOL['legacy']})  deadline {d}")
    print("=" * 74)
    cur = None
    for tier, cid, name, ok, note in out:
        if tier != cur:
            print(f"\n--- Tier {tier} " + "-" * 58); cur = tier
        print(f"  [{'PASS' if ok else 'FAIL'}] {cid:5s} {name}")
        if note: print(f"          {note}")
    fails = [o for o in out if not o[3]]
    print("\n" + "=" * 74)
    print(f"RESULT: {'GO' if not fails else 'NO-GO'} — {len(out)-len(fails)} of {len(out)} checks pass")
    for f in fails:
        print(f"  BLOCKER {f[1]} {f[2]}: {f[4]}")
    print("\nAllocation by firm:")
    for f, p in sorted(pct.items(), key=lambda kv: -kv[1]):
        tag = " (prime)" if f == PRIME["legal_name"] else ""
        print(f"  {p:3d}%  {f}{tag}")
    print("\n--- substring-collision demonstration -------------------------------")
    print("  Requirement 1.8.1 (Public Involvement) vs holder of 11.8.1 only:")
    print(f"    naive string containment  -> {'MATCH (WRONG)' if naive_ok else 'no match'}")
    print(f"    element-wise code compare -> {'match' if strict_ok else 'NO MATCH (CORRECT)'}")
    print("  This solicitation contains both 1.8.1 and 11.8.1. The bug is live here.")
    preclusion_selftest()
    return out, pct, fails

if __name__ == "__main__":
    run()
