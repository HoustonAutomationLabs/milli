"""
First solicitation, 601CT0000006541, re-expressed for the shared engine.

The data is unchanged from gate.py — this only reshapes it to the interface the
engine needs, so that both solicitations run through one set of checks. The
reshaping is itself the finding: ALLOCATION was a category-to-single-firm map,
and the PTC form takes a category-by-firm matrix. On 6541 every category
happened to sit with one firm, so the two were indistinguishable.
"""
from datetime import date
import gate as _g

SOL = dict(_g.SOL)
SOL.update({
    "process": "RFP / SPECIFIC deliverable / FEDERAL / WITH interview / no DBE goal",
    "renewal_window": (date(2026, 1, 1), date(2026, 3, 31)),
    "interview": True,
    "joint_response_allowed": False,
    "deputy_pm_required": False,
    "goal_attr": "dbe",
    "weights": {"technical_approach": 22, "pm_experience": 15,
                "planning_management": 30, "key_staff": 26, "past_performance": 7},
    "narrative_prompts": None,          # general guidance only, no named questions
})

PRIME = dict(_g.PRIME, is_joint_venture=False)
SUBS = _g.SUBS
STAFF = _g.STAFF
PROJECT_MANAGER = _g.PROJECT_MANAGER

# category -> {firm: percent}; every 6541 category sits with exactly one firm
ALLOCATION = {c: {f: SOL["categories"][c][1]} for c, (f, _) in _g.ALLOCATION.items()}
TASK_LEADERS = {c: l for c, (_, l) in _g.ALLOCATION.items()}

if __name__ == "__main__":
    import engine
    engine.run(__import__("sol6541"))
