"""
Fill Attachment 1 (Q-37NY) for 601CT0000006549 using the form's own rules.

Only Attachment 1 can be produced here. On this solicitation Attachment 4 is a
FILLABLE PDF, not the Excel workbook 6541 supplied, so the openpyxl path in
fill_forms.py does not apply to it; and Attachment 3 is generated inside CCIS on
both solicitations. Two of four attachments remain outside this pipeline, for
two different reasons, and the honest count is one of four producible here.

Run with a python that has openpyxl.
"""
import shutil, openpyxl, q_form
import sol6549 as cfg

SRC = "/root/.claude/uploads/5dd1ff1c-cd01-50c6-8995-2bdc6a02bc56"
Q_SRC = f"{SRC}/6de74623-Attachment_1_Cover_Page_Q37NY.xlsx"
OUT = "out"

CONTACT = dict(email="marisol.everly@ocotilloeng.example",
               address="4400 Comal Ridge Blvd, Suite 220, Austin, TX 78744",
               phone="(512) 555-0182", certified_on="2026-09-18")

pm = next(s for s in cfg.STAFF if s["name"] == cfg.PROJECT_MANAGER)


def fname(n, ext):
    stem = f"{cfg.PRIME['legal_name'][:12]}_{cfg.SOL['number'][-6:]}_Att {n}"
    assert len(stem) <= 25, f"{stem!r} is {len(stem)} chars, cap is 25"
    return f"{stem}.{ext}"


out = f"{OUT}/{fname(1,'xlsx')}"
shutil.copy(Q_SRC, out)
wb = openpyxl.load_workbook(out)
ws = wb[q_form.SHEET]
d = q_form.describe(wb)

text_answers = {
    12: cfg.PRIME["legal_name"],
    13: cfg.PRIME["tin"],
    14: cfg.PRIME["ccis_seq"],
    25: pm["name"],
    26: CONTACT["certified_on"],
    27: pm["tx_pe"],
    28: cfg.PRIME["tbpels_firm_reg"],
    29: CONTACT["email"],
    30: CONTACT["address"],
    31: CONTACT["phone"],
}
# Certification rows answer YES; submittal rows answer INCLUDED except
# Attachment 3, which this pipeline cannot produce. Answering INCLUDED for a
# file that is not in the package would be a false statement on a form the PM
# certifies, and RFP s.28 says a false statement may void the response.
dropdown_answers = {r: "YES" for r in range(16, 24)}
dropdown_answers.update({33: "INCLUDED", 34: "INCLUDED",
                         35: "NOT INCLUDED",      # PTC form — CCIS only
                         36: "NOT INCLUDED"})     # Subprovider PDF — not supplied

applied = q_form.fill(ws, d["rules"], d["dropdowns"], d["free_text"],
                      dropdown_answers, text_answers)
wb.save(out)

# ------------------------------------------------------------------- verify
v = openpyxl.load_workbook(out)
vs = v[q_form.SHEET]
dv = q_form.describe(v)
print("=" * 72)
print(f"ATTACHMENT 1 — {cfg.SOL['number']} — {out}")
print("=" * 72)
print(f"  sheets preserved   : {v.sheetnames}")
print(f"  protection         : {vs.protection.sheet}")
print(f"  data validations   : {len(list(vs.data_validations.dataValidation))}")
print(f"  status formula     : {str(vs['H12'].value)[:30]}...")
print(f"  filename           : {fname(1,'xlsx')} "
      f"({len(fname(1,'xlsx').rsplit('.',1)[0])}/25 chars)")
print("\n  rules read from the form (not assumed):")
for gi, g in dv["rules"].items():
    for k, (req, blank) in g.items():
        print(f"    group{gi} {k:<14} comment_required={req}  must_be_blank={blank}")
print("\n  per-row handling:")
for r, val, note in applied:
    print(f"    row {r:<3} {val:<14} {note}")
problems = q_form.audit(vs, dv["rules"], dv["dropdowns"], dv["free_text"])
print("\n" + ("  AUDIT CLEAN — the form's own rules are satisfied on every row"
              if not problems else "  AUDIT PROBLEMS:"))
for r, why in problems:
    print(f"    row {r}: {why}")
