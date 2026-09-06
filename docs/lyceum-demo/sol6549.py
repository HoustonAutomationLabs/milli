"""
Second solicitation: 601CT0000006549 — Routine Bridge Inspection, statewide.

The point of this file is that it is a DIFFERENT SHAPE from 601CT0000006541 and
runs through the same engine. Where 6541 is a federal specific-deliverable
contract with an interview, one award, twenty-seven work categories and a
published preclusion list, this is a non-federal indefinite-deliverable contract
with no interview, TWENTY awards, TWO work categories and no preclusion list at
all. Four of the original gate's assumptions are contradicted here, which is
what a second case is for.

ALL FIRM AND PERSONNEL DATA IS FICTIONAL. The prime carries over from the 6541
run so the two are comparable; its bridge-inspection staff and regional
subproviders are invented for this contract.

Run: python3 sol6549.py
"""
from datetime import date

SOL = {
    "number": "601CT0000006549",
    "posted": date(2026, 9, 1),
    "deadline": date(2026, 9, 22),                 # 1:00 p.m. CT
    "process": "RFP / INDEFINITE deliverable / NON-federal / NO interview / no DBE goal",
    "awards": 20,
    "value_each": 13_500_000,
    "service": "Routine Bridge Inspection Services, Bridge Division, statewide",
    "renewal_window": (date(2026, 1, 1), date(2026, 3, 31)),

    # --- the four assumptions 6541 baked in, all different here
    "admin_qual_required": False,      # RFP s.11: not required to compete
    "precluded_firms": None,           # RFP s.6: the RULE only, no published list
    "interview": False,                # non-federal process without interview
    "major_categories": [],
    "goal_program": None, "goal_pct": 0, "goal_attr": "hub",

    "joint_response_allowed": False,   # RFP s.18: expressly not accepted
    "deputy_pm_required": False,       # RFP s.14
    "core_team_restriction": False,    # RFP s.7
    "min_self_perform_pct": 30,        # RFP s.12(e) — same as 6541
    "page_limit": 10,                  # 6541 was 12

    # Weights INVERT against 6541: there, planning was heaviest at 30 and
    # technical approach 22. Here key staff and technical approach lead, and
    # planning drops ten points. A firm reusing its last page budget puts its
    # longest section on the criterion that fell furthest.
    "weights": {"technical_approach": 29, "pm_experience": 15,
                "planning_management": 20, "key_staff": 30, "past_performance": 6},

    "categories": {
        "6.1.1": ("Routine Bridge Inspection Team Leader", 80),
        "6.1.2": ("Routine Bridge Inspection Project Manager", 20),
    },

    # 6541 gave general guidance. This RFP asks four questions by name, each
    # demanding a specific worked example. They are checkable: a proposal that
    # never mentions scour has left a named question unanswered.
    "narrative_prompts": [
        dict(id="P1", criterion="technical_approach",
             ask="Technical approach and experience identifying and evaluating "
                 "CRITICAL FINDINGS. Include ONE example of a bridge inspection "
                 "where the team identified a critical finding. State the criteria "
                 "used, and the process distinguishing routine deficiencies from "
                 "true critical findings.",
             must_mention=["critical finding"], needs_example=True),
        dict(id="P2", criterion="technical_approach",
             ask="Technical approach and experience performing BRIDGE LOAD RATINGS "
                 "for simple-span, continuous-span and non-typical configurations. "
                 "Include ONE example of incorporating inspection findings into "
                 "structural analysis, interpreting results, and ensuring accuracy.",
             must_mention=["load rating", "simple-span", "continuous-span",
                           "non-typical"], needs_example=True),
        dict(id="P3", criterion="technical_approach",
             ask="Technical approach and experience in BRIDGE SCOUR evaluation and "
                 "assessment: identifying, analysing and monitoring scour, and the "
                 "factors weighed against foundations and structural performance.",
             must_mention=["scour"], needs_example=False),
        dict(id="P4", criterion="pm_experience",
             ask="The PROJECT MANAGER's experience and approach managing bridge "
                 "inspection programmes; the anticipated inspection SCHEDULE "
                 "including typical days and hours; availability for coordination "
                 "with TxDOT staff and QA/QC; and inspection ACCESS METHODS.",
             must_mention=["schedule", "access"], needs_example=False),
    ],
}

# ------------------------------------------------------------- fictional firms
PRIME = {
    "legal_name": "Ocotillo Engineering Group, LLC",
    "tin": "17412900355", "ccis_seq": "00004417", "tbpels_firm_reg": "F-22841",
    "sos_registered": True, "precert_active": True,
    "precert_renewed": date(2026, 2, 17),
    "admin_qual": {"status": "Effective", "rate_expires": date(2027, 3, 31)},
    "hub": False, "dbe": False, "affiliates": ["Ocotillo Field Services, LLC"],
    "former_txdot_staff": [{"name": "R. Alvarez", "left": date(2022, 6, 30)}],
    "e_verify": True, "ndaa_clear": True, "is_joint_venture": False,
}

SUBS = {
    "Pecos Valley Bridge Inspection, LLC": dict(
        precert_active=True, precert_renewed=date(2026, 2, 3), sos_registered=True,
        admin_qual={"status": "Safe harbor", "rate_expires": None},
        hub=True, hub_expires=date(2028, 6, 30), dbe=False,
        ndaa_clear=True, affiliates=[], region="West Texas"),
    "Neches River Structural Services, Inc.": dict(
        precert_active=True, precert_renewed=date(2026, 1, 30), sos_registered=True,
        admin_qual={"status": "Effective", "rate_expires": date(2027, 9, 30)},
        hub=False, dbe=False, ndaa_clear=True, affiliates=[], region="East Texas"),
    "Panhandle Structures Group, LLC": dict(
        precert_active=True, precert_renewed=date(2026, 3, 19), sos_registered=True,
        admin_qual={"status": "Effective", "rate_expires": date(2027, 4, 30)},
        hub=True, hub_expires=date(2027, 11, 30), dbe=False,
        ndaa_clear=True, affiliates=[], region="Panhandle / North"),
}

STAFF = [
    dict(name="Marisol Everly, P.E.", firm="Ocotillo Engineering Group, LLC",
         ccis_emp_seq="000031882", tx_pe="118432", pe_expires=date(2027, 12, 31),
         precerts=["6.1.2", "11.2.1", "11.3.1"], denied=[], pending=[], years=19,
         role="Project Manager", committed_pursuits=[]),
    dict(name="Dov Ranganathan, P.E.", firm="Ocotillo Engineering Group, LLC",
         ccis_emp_seq="000029104", tx_pe="104778", pe_expires=date(2027, 12, 31),
         precerts=["6.1.1", "6.1.2", "11.2.1"], denied=[], pending=[], years=22,
         role="Routine Bridge Inspection Team Leader", committed_pursuits=[]),
    dict(name="Sunniva Okonkwo, P.E.", firm="Pecos Valley Bridge Inspection, LLC",
         ccis_emp_seq="000036402", tx_pe="131774", pe_expires=date(2028, 12, 31),
         precerts=["6.1.1"], denied=[], pending=["6.1.2"], years=14,
         role="Regional inspection lead — West", committed_pursuits=[]),
    dict(name="Emeric Vandersloot, P.E.", firm="Neches River Structural Services, Inc.",
         ccis_emp_seq="000030871", tx_pe="109233", pe_expires=date(2027, 12, 31),
         precerts=["6.1.1", "6.1.2"], denied=[], pending=[], years=26,
         role="Regional inspection lead — East", committed_pursuits=[]),
    dict(name="Britt Sandoval-Ng, P.E.", firm="Panhandle Structures Group, LLC",
         ccis_emp_seq="000034663", tx_pe="127018", pe_expires=date(2028, 12, 31),
         precerts=["6.1.1"], denied=[], pending=[], years=17,
         role="Regional inspection lead — North", committed_pursuits=[]),
]

# A category is split ACROSS FIRMS. Both RFPs ask for "the percentage of work
# anticipated for each firm for each category", and with two categories at 80/20
# the difference is structural: the prime cannot reach its 30% floor out of the
# 20% management category, so it must hold a slice of the 80% inspection
# category. A one-firm-per-category model cannot express this contract at all.
ALLOCATION = {
    "6.1.1": {"Ocotillo Engineering Group, LLC": 25,
              "Pecos Valley Bridge Inspection, LLC": 20,
              "Neches River Structural Services, Inc.": 20,
              "Panhandle Structures Group, LLC": 15},
    "6.1.2": {"Ocotillo Engineering Group, LLC": 20},
}

# One task leader per work category, regardless of how many firms perform it.
TASK_LEADERS = {
    "6.1.1": "Dov Ranganathan, P.E.",
    "6.1.2": "Marisol Everly, P.E.",
}

PROJECT_MANAGER = "Marisol Everly, P.E."

if __name__ == "__main__":
    import engine
    engine.run(__import__("sol6549"))
