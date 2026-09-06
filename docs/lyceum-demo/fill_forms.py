"""
Fill Attachment 1 (Q-59ES questionnaire) and Attachment 4 (Subprovider Info)
for the fictional firm. Writes CELL VALUES ONLY into the vendor-supplied
workbooks -- never regenerates them -- so sheet protection, data validation and
the status formulas survive intact. The RFP warns that altering the structure or
saving in another format invalidates the submission.
"""
import shutil, sys, os, subprocess, openpyxl
from gate import PRIME, SUBS, STAFF, ALLOCATION, PROJECT_MANAGER, CONTACTED_NOT_TEAMED, SOL

SRC = "/root/.claude/uploads/5dd1ff1c-cd01-50c6-8995-2bdc6a02bc56"
Q_SRC = f"{SRC}/902ce732-Attachment_1_Cover_Page_Q59ES.xlsx"
S_SRC = f"{SRC}/8c0f997d-601CT0000006541_Subprovider_Info.xlsx"
OUT = "out"

# file naming: first 12 chars of legal name _ last 6 of solicitation _ Att N, <=25 chars
def fname(n, ext):
    stem = f"{PRIME['legal_name'][:12]}_{SOL['number'][-6:]}_Att {n}"
    assert len(stem) <= 25, f"{stem!r} is {len(stem)} chars, cap is 25"
    return f"{stem}.{ext}"

pm = next(s for s in STAFF if s["name"] == PROJECT_MANAGER)

# ---------------------------------------------------------------- Attachment 1
q_out = f"{OUT}/{fname(1,'xlsx')}"
shutil.copy(Q_SRC, q_out)
wb = openpyxl.load_workbook(q_out)
ws = wb["1"]

# GENERAL + ATTESTATION -> free text in the Comment column (G)
comments = {
    "G12": PRIME["legal_name"],
    "G13": PRIME["tin"],
    "G14": PRIME["ccis_seq"],
    "G25": pm["name"],
    "G26": "2026-09-18",
    "G27": pm["tx_pe"],
    "G28": PRIME["tbpels_firm_reg"],
    "G29": "marisol.everly@ocotilloeng.example",
    "G30": "4400 Comal Ridge Blvd, Suite 220, Austin, TX 78744",
    "G31": "(512) 555-0182",
}
# CERTIFICATION (F16:F23) and SUBMITTAL CONTENTS (F33:F36) -> dropdown value in F.
# The hidden Response Options sheet marks BOTH options "comment must be blank",
# so G must be left empty on these rows or the status cell reports an error.
responses = {f"F{r}": "YES" for r in range(16, 24)}
responses.update({f"F{r}": "INCLUDED" for r in range(33, 37)})

ws.protection.sheet = False                     # unlock to write
for ref, val in {**comments, **responses}.items():
    ws[ref] = val
ws.protection.sheet = True                      # re-lock exactly as supplied
wb.save(q_out)

# ---------------------------------------------------------------- Attachment 4
s_out = f"{OUT}/{fname(4,'xlsx')}"
shutil.copy(S_SRC, s_out)
wb2 = openpyxl.load_workbook(s_out)
w = wb2["Sheet1"]
w["C2"] = PRIME["legal_name"]
w["C3"] = "Yes" if PRIME["dbe"] else "No"
w["C4"] = "Yes" if PRIME["hub"] else "No"

CONTACTS = {
    "Barton Creek Materials Testing, LLC": ("Corbin Ashworth", "1180 Slaughter Ln, Austin, TX 78748", "c.ashworth@bartoncreekmt.example", "(512) 555-0114"),
    "Caliche Geotechnical, Inc.":          ("Halvard Nkemelu, P.E.", "905 Fisk Ave, Round Rock, TX 78664", "h.nkemelu@calichegeo.example", "(512) 555-0139"),
    "Pecan Bayou Survey Company":          ("Rosalind Tejeda, R.P.L.S.", "27 Live Oak St, Georgetown, TX 78626", "r.tejeda@pecanbayousurvey.example", "(512) 555-0157"),
    "Windrow Public Affairs, LLC":         ("Junnosuke Abelard", "610 Guadalupe St, Austin, TX 78701", "j.abelard@windrowpa.example", "(512) 555-0166"),
    "Llano Utility Coordination, LLC":     ("Ottoline Kirkbride, P.E.", "2201 Airport Rd, Cedar Park, TX 78613", "o.kirkbride@llanoutility.example", "(512) 555-0173"),
    "Blanco Environmental Services, LLC":  ("Ferris Onwuachi, P.E.", "88 Barton Springs Rd, Austin, TX 78704", "f.onwuachi@blancoenv.example", "(512) 555-0148"),
    "Sabine Valley Inspection Services, LLC": ("Delphine Marchetti", "410 Pine St, Kilgore, TX 75662", "d.marchetti@sabinevalleyinsp.example", "(903) 555-0121"),
    "Trinity Forks Testing Group, LLC":    ("Augustin Pell", "77 Elm St, Denton, TX 76201", "a.pell@trinityforkstesting.example", "(940) 555-0198"),
    "Guadalupe Bend Constructability Advisors, LLC": ("Nadia Oyelaran, P.E.", "1500 River Rd, New Braunfels, TX 78130", "n.oyelaran@guadalupebendca.example", "(830) 555-0104"),
}
def cert_status(f):
    s = SUBS.get(f)
    if not s: return "N/A"
    if s.get("dbe") and s.get("hub"): return "DBE&HUB"
    if s.get("dbe"): return "DBE"
    if s.get("hub"): return "HUB"
    return "N/A"

rows = [(f, True) for f in SUBS] + [(f, False) for f, _ in CONTACTED_NOT_TEAMED]
r = 7
for firm, on_team in rows:
    c = CONTACTS[firm]
    w[f"A{r}"], w[f"B{r}"], w[f"C{r}"] = c[0], firm, c[1]
    w[f"D{r}"], w[f"E{r}"] = c[2], c[3]
    w[f"F{r}"] = cert_status(firm)
    w[f"G{r}"] = "Yes" if on_team else "No"
    r += 1

# Signature block, and the vendor template's print-area defect. Both were missed
# on the first run: reading named cells never looked below the data rows, and
# nothing rendered the sheet to see what a reviewer would. See fill6549_sub.py
# for the full note — the template's print area stops at row 46 while the
# printed-name and title cells are on row 47.
w["A45"] = w["A47"] = pm["name"]        # electronic signature accepted
w["E45"], w["E47"] = "2026-09-18", "Project Manager"
if w.print_area and w.print_area.endswith("$H$46"):
    w.print_area = w.print_area.replace("$H$46", "$H$47")
wb2.save(s_out)

# Attachment 4 is SUBMITTED AS PDF on both solicitations -- "The fillable file
# posted with the solicitation must be completed and submitted as a PDF file."
# The .xlsx is the working file; uploading it is non-responsive on format alone.
s_pdf = f"{OUT}/{fname(4,'pdf')}"
subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", OUT, s_out],
               capture_output=True, text=True, timeout=180)
if not os.path.exists(s_pdf):
    print("WARNING: Attachment 4 PDF export failed — the .xlsx alone is not submittable")

# ---------------------------------------------------------------- verification
print("VERIFY — re-reading what was written\n" + "="*66)
for path, sheet in [(q_out, "1"), (s_out, "Sheet1")]:
    v = openpyxl.load_workbook(path)
    vs = v[sheet]
    print(f"\n{path}")
    print(f"  sheets preserved : {v.sheetnames}")
    print(f"  protection       : {vs.protection.sheet}")
    dvs = list(vs.data_validations.dataValidation)
    print(f"  data validations : {len(dvs)} preserved")
    for dv in dvs: print(f"      {dv.formula1} @ {dv.sqref}")
if True:
    v = openpyxl.load_workbook(q_out); vs = v["1"]
    bad = [f"G{r}" for r in list(range(16,24))+list(range(33,37)) if vs[f"G{r}"].value]
    print(f"\n  Q-59ES comment-must-be-blank rows violated: {bad or 'none'}")
    filled = sum(1 for r in range(11,37) if vs[f"F{r}"].value not in (None,"","-") or vs[f"G{r}"].value)
    print(f"  Q-59ES answered rows: {filled} of 22")
    print(f"  status formulas intact: {str(vs['H12'].value)[:28]}...")
if os.path.exists(s_pdf):
    from pypdf import PdfReader
    flat = " ".join("\n".join(p.extract_text() or "" for p in PdfReader(s_pdf).pages).split())
    miss = [f for f, _ in rows if " ".join(f.split()) not in flat]
    print(f"\n  Attachment 4 SUBMITTED FILE: {s_pdf} ({os.path.getsize(s_pdf):,} bytes)")
    print(f"  every listed firm survives the export: {'yes' if not miss else 'NO ' + str(miss)}")
    print(f"  signature block in export: "
          f"{'complete' if pm['name'] in flat and 'Project Manager' in flat else 'INCOMPLETE'}")
print(f"\nFilenames: {fname(1,'xlsx')} / {fname(4,'pdf')} "
      f"({len(fname(4,'pdf').rsplit('.',1)[0])}/25 chars)")
