"""Mechanical responsiveness checks — the ones that void a submission."""
import re, os, openpyxl, q_form
from gate import PRIME, SOL, ALLOCATION, PROJECT_MANAGER, STAFF

OUT="out"; NARR=f"{OUT}/proposal_draft.md"
r=[]
def c(cid,name,ok,note=""): r.append((cid,name,ok,note))

# --- 0.6 file naming: first 12 chars _ last 6 digits _ Att N, stem <= 25 chars
for n,ext in [(1,"xlsx"),(4,"xlsx")]:
    stem=f"{PRIME['legal_name'][:12]}_{SOL['number'][-6:]}_Att {n}"
    f=f"{stem}.{ext}"
    c(f"0.6.{n}", f"Filename convention — Att {n}",
      len(stem)<=25 and os.path.exists(f"{OUT}/{f}"), f"{f} ({len(stem)}/25 chars)")

# --- 0.2 every requested-information slot filled
# The portal's Requested Information table states an upload type PER SLOT, and
# that table is the authority -- not the format of the template you downloaded.
# Attachment 1 is Excel; 2, 3 and 4 are PDF. The first version of this check
# verified only that a file existed, and passed an .xlsx sitting in the
# Attachment 4 slot, which is non-responsive on format alone.
stem=f"{OUT}/{PRIME['legal_name'][:12]}_{SOL['number'][-6:]}_Att"
slots={"Attachment 1 Cover Page":(f"{stem} 1.xlsx",".xlsx"),
       "Attachment 2 Proposal":(NARR,".pdf"),
       "Attachment 3 PTC Form":(None,".pdf"),
       "Attachment 4 Subprovider Info":(f"{stem} 4.pdf",".pdf")}
missing=[k for k,(v,_) in slots.items() if v is None or not os.path.exists(v)]
c("0.2","All four requested-information slots filled", not missing,
  "PTC form must be generated in CCIS/Salesforce — cannot be produced here" if missing else "")
wrong=[f"{k}: {os.path.splitext(v)[1]} where the portal requires {want}"
       for k,(v,want) in slots.items()
       if v and os.path.exists(v) and not v.lower().endswith(want)]
c("0.2b","Each slot holds the file type the portal requires", not wrong,
  "; ".join(wrong) if wrong else
  "Att 1 .xlsx; Att 2 and 4 .pdf (Att 2 renders from markdown at submission)")

# --- 0.11 / 29a page limit
t=open(NARR).read()
body=re.sub(r'[#*_>`|\-]',' ',re.sub(r'\*Budget:[^*]*\*','',t))
pages=len(body.split())/550
c("29a",f"Proposal within {SOL['page_limit']}-page limit", pages<=SOL["page_limit"],
  f"~{pages:.1f} pages estimated at 550 w/pg")

# --- 29c banned elements
banned={"hyperlink":r'https?://', "QR code":r'(?i)qr code',
        "table of contents":r'(?i)^#+\s*table of contents', "cover letter":r'(?i)^#+\s*cover letter'}
hits=[k for k,pat in banned.items() if re.search(pat,t,re.M)]
c("29c","No hyperlinks, QR codes, cover page, letter or TOC", not hits, ", ".join(hits))

# --- 28 cross-document consistency
wb=openpyxl.load_workbook(f"{OUT}/{PRIME['legal_name'][:12]}_{SOL['number'][-6:]}_Att 1.xlsx")
ws=wb["1"]
pm_on_form=(ws["G25"].value or "").strip()
c("28.1","PM in proposal matches PM on the questionnaire",
  pm_on_form==PROJECT_MANAGER and PROJECT_MANAGER.split(",")[0] in t,
  f"questionnaire: {pm_on_form}")
c("28.2","Prime legal name identical on questionnaire and proposal",
  (ws["G12"].value or "").strip()==PRIME["legal_name"] and PRIME["legal_name"] in t)

# --- 28.3 "Task Leader" used only for precertified, PTC-listed people.
# A loose regex flags pronouns and sentence-initial words; require the candidate to
# look like a person reference — an honorific-bearing name or a known surname.
leaders={l for _,l in ALLOCATION.values()}
surnames={l.split(",")[0].split()[-1] for l in leaders}
STOP={"He","She","They","The","Our","Each","Every","A","An","This","That","Their",
      "Differing","Materials","Utility","Survey","Public","Geotechnical","Night",
      "Environmental","Scheduling","Bridge","Roadway","Construction","ELIT","Where","Work"}
bad=[]
for sent in re.split(r'(?<=[.!?])\s+', t):
    if not re.search(r'(?i)task lead', sent): continue
    # person references: "Mr./Ms. X", "X, P.E.", or a bare known surname
    cands=set(re.findall(r'\b(?:Mr\.|Ms\.|Dr\.)\s+([A-Z][a-zA-Z\-]+)', sent))
    cands |= set(re.findall(r'\b([A-Z][a-zA-Z\-]+),\s*(?:P\.E\.|R\.P\.L\.S\.)', sent))
    cands |= {w for w in re.findall(r'\b([A-Z][a-zA-Z\-]+)\b', sent)
              if w in surnames}
    bad += [n for n in cands if n not in surnames and n not in STOP]
c("28.3",'"Task Leader" used only for precertified, PTC-listed staff', not bad,
  str(sorted(set(bad))) if bad else
  f"{len(leaders)} named leaders, all precertified in their category")

# --- 0.8 cover page completeness incl. PM certification
rows=list(range(12,15))+list(range(16,24))+list(range(25,32))+list(range(33,37))
incomplete=[f"C{ws[f'C{x}'].value}" for x in rows
            if (ws[f"F{x}"].value in (None,"","-")) and not ws[f"G{x}"].value]
c("0.8","Cover page complete (all 22 rows answered)", not incomplete, str(incomplete) if incomplete else "22/22")

# --- comment rules READ FROM THE FORM, not assumed. Q-59ES and Q-37NY look
# identical and disagree on this: 6541 forbids a comment on the submittal rows,
# 6549 permits one. Hardcoding the rule passes here and would misreport there.
_d=q_form.describe(wb)
viol=q_form.audit(ws,_d["rules"],_d["dropdowns"],_d["free_text"])
c("Q1","Every row satisfies the form's own response/comment rules", not viol,
  str(viol) if viol else
  "; ".join(f"group{g} {k} must_be_blank={v[1]}"
            for g,gr in _d["rules"].items() for k,v in list(gr.items())[:1]))

# --- workbook integrity
c("Q2","Sheet protection, validation and formulas preserved",
  ws.protection.sheet and len(list(ws.data_validations.dataValidation))==2
  and str(ws["H12"].value).startswith("=IF"))

print("="*72); print("MECHANICAL CHECKS"); print("="*72)
for cid,name,ok,note in r:
    print(f"  [{'PASS' if ok else 'FAIL'}] {cid:6s} {name}")
    if note: print(f"           {note}")
f=[x for x in r if not x[2]]
print("="*72)
print(f"{len(r)-len(f)} of {len(r)} pass" + ("" if not f else f" — {len(f)} BLOCKING"))
