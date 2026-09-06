"""
Attachment 4 for 601CT0000006549 — fill the Excel template, then export to PDF.

The export is the point. Both RFPs say the same thing and I read it wrong once:

    "The fillable file posted with the solicitation must be completed and
     submitted as a PDF file... PEPS recommends using the 'Print to PDF'
     function to flatten PDF files and submit as a single PDF file."

The template is Excel on both solicitations; the SUBMISSION is PDF on both. The
portal's Requested Information table is the authority on the upload type, not
the format of the template you downloaded — Attachment 1 is Excel there,
Attachments 2, 3 and 4 are PDF. An .xlsx uploaded to the Attachment 4 slot is
non-responsive on format alone, and no amount of correct content saves it.

The two subprovider templates are structurally identical — same sheet, same
header row, same two validations — differing only in the solicitation number in
C1, so one filler serves both.

Run with a python that has openpyxl; requires libreoffice for the export.
"""
import shutil, subprocess, os, sys, openpyxl
import sol6549 as cfg

SRC = "/root/.claude/uploads/5dd1ff1c-cd01-50c6-8995-2bdc6a02bc56/e70251b4-SUB_TEMPL.xlsx"
OUT = "out"
FIRST_ROW = 7

CONTACTS = {
    "Pecos Valley Bridge Inspection, LLC": (
        "Sunniva Okonkwo, P.E.", "1420 Bessemer Ave, Odessa, TX 79761",
        "s.okonkwo@pecosvalleybi.example", "(432) 555-0143"),
    "Neches River Structural Services, Inc.": (
        "Emeric Vandersloot, P.E.", "308 Calder Ave, Beaumont, TX 77701",
        "e.vandersloot@nechesriverstruct.example", "(409) 555-0177"),
    "Panhandle Structures Group, LLC": (
        "Britt Sandoval-Ng, P.E.", "2115 Coulter St, Amarillo, TX 79106",
        "b.sandovalng@panhandlestructures.example", "(806) 555-0192"),
    # contacted during teaming, not engaged. The form asks for these too: it
    # wants every firm CONTACTED, with a column marking who is on the team.
    "Sabine Valley Inspection Services, LLC": (
        "Delphine Marchetti", "410 Pine St, Kilgore, TX 75662",
        "d.marchetti@sabinevalleyinsp.example", "(903) 555-0121"),
    "Caprock Bridge Testing, LLC": (
        "Augustin Pell", "77 Ave H, Lubbock, TX 79401",
        "a.pell@caprockbridge.example", "(806) 555-0158"),
}
CONTACTED_NOT_TEAMED = ["Sabine Valley Inspection Services, LLC",
                        "Caprock Bridge Testing, LLC"]

# The form carries a SIGNATURE BLOCK below the data rows, in merged cells the
# labels sit above. Reading named cells missed it entirely; it only became
# visible when the sheet was rendered to PDF and read as a page. The 6541
# Attachment 4 delivered earlier is missing it too — the templates are the same
# form. An unsigned attachment is a responsiveness risk on a document that
# "will become part of an awarded contract".
SIG = {"A45": None,          # signature — the PM signs, not the drafting service
       "E45": "2026-09-18",  # date
       "A47": None,          # printed name
       "E47": "Project Manager"}


def fname(n, ext):
    stem = f"{cfg.PRIME['legal_name'][:12]}_{cfg.SOL['number'][-6:]}_Att {n}"
    assert len(stem) <= 25, f"{stem!r} is {len(stem)} chars, cap is 25"
    return f"{stem}.{ext}"


def cert_status(firm):
    s = cfg.SUBS.get(firm)
    if not s:
        return "N/A"
    tags = [t for t, k in (("DBE", "dbe"), ("HUB", "hub")) if s.get(k)]
    return "&".join(tags) if tags else "N/A"


xlsx = f"{OUT}/{fname(4,'xlsx')}"
shutil.copy(SRC, xlsx)
wb = openpyxl.load_workbook(xlsx)
ws = wb["Sheet1"]
ws["C2"] = cfg.PRIME["legal_name"]
ws["C3"] = "Yes" if cfg.PRIME.get("dbe") else "No"
ws["C4"] = "Yes" if cfg.PRIME.get("hub") else "No"

rows = [(f, True) for f in cfg.SUBS] + [(f, False) for f in CONTACTED_NOT_TEAMED]
r = FIRST_ROW
for firm, on_team in rows:
    name, addr, email, phone = CONTACTS[firm]
    ws[f"A{r}"], ws[f"B{r}"], ws[f"C{r}"] = name, firm, addr
    ws[f"D{r}"], ws[f"E{r}"] = email, phone
    ws[f"F{r}"] = cert_status(firm)
    ws[f"G{r}"] = "Yes" if on_team else "No"
    r += 1

pm = next(x for x in cfg.STAFF if x["name"] == cfg.PROJECT_MANAGER)
SIG["A45"] = pm["name"]          # electronic signature accepted -> typed name
SIG["A47"] = pm["name"]
for ref, val in SIG.items():
    ws[ref] = val

# The vendor template's own print area is $A$1:$H$46, but the answer cells for
# "Printed (or typed) Name" and "Title" are on row 47 — the labels are on 46 and
# the merged answer cells sit below them. So the form as supplied exports a PDF
# with those two fields blank no matter what was typed into them. It is true of
# both solicitations' templates.
#
# That is a defect in TxDOT's file, and it lands on the bidder: fill the form in
# Excel, "Print to PDF" exactly as PEPS recommends, upload, and you have
# submitted an unsigned-looking form. Extending the print area by one row
# changes no content and no structure; it makes the PDF contain what the
# spreadsheet says. Anything less would be submitting a document that does not
# match its own source.
if ws.print_area and ws.print_area.endswith("$H$46"):
    ws.print_area = ws.print_area.replace("$H$46", "$H$47")
    print(f"  print area extended to {ws.print_area} — vendor template stops at row 46,\n"
          f"  which excludes the printed-name and title cells on row 47")
wb.save(xlsx)

# ------------------------------------------------------------------ to PDF
pdf = f"{OUT}/{fname(4,'pdf')}"
res = subprocess.run(
    ["soffice", "--headless", "--convert-to", "pdf", "--outdir", OUT, xlsx],
    capture_output=True, text=True, timeout=180)
if not os.path.exists(pdf):
    print("PDF EXPORT FAILED\n", res.stdout, res.stderr)
    sys.exit(1)

# ----------------------------------------------------------------- verify
from pypdf import PdfReader
rd = PdfReader(pdf)
text = "\n".join(p.extract_text() or "" for p in rd.pages)
print("=" * 74)
print(f"ATTACHMENT 4 — {cfg.SOL['number']}")
print("=" * 74)
print(f"  worksheet filled  : {xlsx}")
print(f"  SUBMITTED FILE    : {pdf}   ({os.path.getsize(pdf):,} bytes, "
      f"{len(rd.pages)} page(s))")
print(f"  filename          : {fname(4,'pdf')} "
      f"({len(fname(4,'pdf').rsplit('.',1)[0])}/25 chars)")
print(f"  single PDF, no attachments: {'/Names' not in rd.trailer.get('/Root', {})}")

# Match on whitespace-normalised text: the PDF wraps long firm names across
# lines, and an exact substring test reports a firm as missing when it is
# present and merely broken by a line ending. The first version of this check
# did exactly that and raised two false alarms.
flat = " ".join(text.split())
missing = [f for f, _ in rows if " ".join(f.split()) not in flat]
print(f"\n  every listed firm survives the export: "
      f"{'yes' if not missing else 'NO — ' + str(missing)}")
print(f"  prime name in export : {'yes' if cfg.PRIME['legal_name'] in text else 'NO'}")
print(f"  rows written         : {len(rows)} "
      f"({sum(1 for _, t in rows if t)} on team, "
      f"{sum(1 for _, t in rows if not t)} contacted only)")
sig_ok = all(" ".join(str(v).split()) in flat for v in SIG.values())
print(f"  signature block      : {'complete' if sig_ok else 'INCOMPLETE'} "
      f"(name, printed name, title, date)")
print("\n  NOTE: the .xlsx is the working file. The .pdf is what gets uploaded.")
