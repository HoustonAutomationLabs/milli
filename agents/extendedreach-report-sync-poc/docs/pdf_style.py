"""Shared look and feel for the printed documents in docs/.

Extracted so the setup guide and the Chrome prompt sheet cannot drift apart:
one palette, one set of styles, one callout, one table.

On glyphs: ReportLab's built-in fonts use WinAnsi encoding, so en dashes, em
dashes and curly quotes render correctly (verified, not assumed). Arrows and
check marks do NOT, and a missing glyph renders as a solid black box, so these
documents stay clear of them.

    ./.venv/bin/pip install reportlab pypdf     # build-only dependencies

They are deliberately not in requirements.txt: the tool itself does not need
them, and a scheduled job should install as little as possible.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent / "ExtendedReach-Sync-Setup-Guide.pdf"

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#5c5c5c")
RULE = colors.HexColor("#d8d4cc")
ACCENT = colors.HexColor("#8a4b2a")
CODE_BG = colors.HexColor("#f4f2ee")
WARN_BG = colors.HexColor("#fdf3e7")
WARN_EDGE = colors.HexColor("#c8873f")
NOTE_BG = colors.HexColor("#eef2f4")
NOTE_EDGE = colors.HexColor("#6d8894")

MARGIN = 0.85 * inch

styles = getSampleStyleSheet()


def S(name, **kw):
    base = kw.pop("parent", styles["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


BODY = S("body", fontName="Helvetica", fontSize=10, leading=14.5,
         textColor=INK, spaceAfter=8, alignment=TA_LEFT)
LEAD = S("lead", parent=BODY, fontSize=11.5, leading=17, spaceAfter=12)
H1 = S("h1", fontName="Helvetica-Bold", fontSize=19, leading=23,
       textColor=INK, spaceBefore=0, spaceAfter=4)
# keepWithNext stops a heading being left stranded at the foot of a page with
# its content overleaf.
H2 = S("h2", fontName="Helvetica-Bold", fontSize=13.5, leading=17,
       textColor=INK, spaceBefore=18, spaceAfter=7, keepWithNext=1)
H3 = S("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14,
       textColor=ACCENT, spaceBefore=12, spaceAfter=4, keepWithNext=1)
KICKER = S("kicker", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
           textColor=ACCENT, spaceAfter=3)
CODE = S("code", fontName="Courier-Bold", fontSize=9, leading=13.5,
         textColor=colors.HexColor("#26221d"), spaceAfter=0)
CODE_OUT = S("codeout", fontName="Courier", fontSize=8.5, leading=12,
             textColor=MUTED, spaceAfter=0)
SMALL = S("small", parent=BODY, fontSize=9, leading=13, textColor=MUTED)
CELL = S("cell", fontName="Helvetica", fontSize=8.8, leading=12, textColor=INK)
CELLB = S("cellb", parent=CELL, fontName="Helvetica-Bold")
CELLC = S("cellc", fontName="Courier", fontSize=8.3, leading=11.5, textColor=INK)


def para(text, style=BODY):
    return Paragraph(text, style)


def code(*lines, output=False):
    """A shaded command block. `output` renders it as terminal output."""
    style = CODE_OUT if output else CODE
    rows = [[Paragraph(line.replace(" ", "&nbsp;") if line.startswith(" ") else line,
                       style)] for line in lines]
    t = Table(rows, colWidths=[6.3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 1),
        ("LINEBEFORE", (0, 0), (0, -1), 2, ACCENT if not output else RULE),
    ]))
    return t


def callout(title, body, kind="note"):
    bg, edge = (WARN_BG, WARN_EDGE) if kind == "warn" else (NOTE_BG, NOTE_EDGE)
    inner = [[Paragraph(title, S("ct", fontName="Helvetica-Bold", fontSize=9,
                                 leading=12, textColor=edge, spaceAfter=3))],
             [Paragraph(body, S("cb", parent=BODY, fontSize=9, leading=13,
                                spaceAfter=0))]]
    t = Table(inner, colWidths=[6.1 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 0),
        ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
    ]))
    return t


def table(header, rows, widths):
    """A simple data table.

    Pass header=None (or a row of empty strings) for a table that is really a
    two-column layout rather than data: an empty grey header bar reads as a
    mistake.
    """
    has_header = bool(header) and any(h.strip() for h in header)
    data = [[Paragraph(h, CELLB) for h in header]] if has_header else []
    for row in rows:
        data.append([Paragraph(c, CELLC if c.startswith(("./", "python", "cp ",
                                                         "git ", "open ", "grep",
                                                         "launchctl"))
                               else CELL) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if has_header else 0)
    style = [
        ("LINEBELOW", (0, 1 if has_header else 0), (-1, -2), 0.4,
         colors.HexColor("#eae7e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if has_header:
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efece6")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, RULE),
        ] + style
    t.setStyle(TableStyle(style))
    return t


def step_head(number, title, minutes):
    """A numbered step banner."""
    left = Paragraph(f"STEP {number}", S("sn", fontName="Helvetica-Bold",
                                         fontSize=8.5, leading=11,
                                         textColor=colors.white))
    mid = Paragraph(title, S("st", fontName="Helvetica-Bold", fontSize=12.5,
                             leading=16, textColor=INK))
    right = Paragraph(minutes, S("sm", fontName="Helvetica", fontSize=8.5,
                                 leading=11, textColor=MUTED))
    badge = Table([[left]], colWidths=[0.72 * inch])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    t = Table([[badge, mid, right]], colWidths=[0.82 * inch, 4.5 * inch, 1.1 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.8, RULE),
    ]))
    return t



# (label, title shown, key). PROBES maps each key to a string that appears on
# the page the section starts on, so the page numbers are measured from the
# built document rather than typed by hand and left to drift.
TOC_ENTRIES = [
    ("", "Before you begin: what you need to have ready", "before"),
    ("", "How it works, in plain English", "how"),
    ("Step 1", "Get the software onto your Mac", "s1"),
    ("Step 2", "Install it", "s2"),
    ("Step 3", "Create your settings file", "s3"),
    ("Step 4", "Connect Google Drive", "s4"),
    ("Step 5", "Show it your reports (repeat per report)", "s5"),
    ("Step 6", "Tell it what a good file looks like", "s6"),
    ("Step 7", "Test run — nothing gets uploaded", "s7"),
    ("Step 8", "The first real run", "s8"),
    ("Step 9", "Turn on the daily schedule", "s9"),
    ("", "Your weekly two-minute check", "weekly"),
    ("", "When something goes wrong", "trouble"),
    ("", "What this tool will never do", "never"),
    ("", "Words this guide uses", "glossary"),
    ("", "One-page command reference", "quickref"),
]

# Each probe must appear ONLY in the section body, never in the contents table
# itself — otherwise every section resolves to the contents page. The step
# badges render as "STEP 1" in capitals while the contents says "Step 1", which
# is enough to tell them apart; the rest use a distinctive opening sentence.
PROBES = {
    "before": "Five things to have ready",
    "how": "Nine things happen, in order",
    "s1": "STEP 1",
    "s2": "STEP 2",
    "s3": "STEP 3",
    "s4": "STEP 4",
    "s5": "STEP 5",
    "s6": "STEP 6",
    "s7": "STEP 7",
    "s8": "STEP 8",
    "s9": "STEP 9",
    "weekly": "Automation fails quietly",
    "trouble": "Every run ends with a number",
    "never": "These are enforced in the code",
    "glossary": "The Mac app where you type commands",
    "quickref": "Every command starts by going to the project folder",
}




# ---------------------------------------------------------------------------
# Page furniture
# ---------------------------------------------------------------------------

def make_on_page(running_head: str):
    """A header rule and page number on every page but the cover."""

    def on_page(canvas, doc):
        canvas.saveState()
        w, h = LETTER
        if doc.page > 1:
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(MUTED)
            canvas.drawString(MARGIN, h - MARGIN + 22, running_head)
            canvas.setStrokeColor(RULE)
            canvas.setLineWidth(0.5)
            canvas.line(MARGIN, h - MARGIN + 14, w - MARGIN, h - MARGIN + 14)
            canvas.drawRightString(w - MARGIN, 0.55 * inch, str(doc.page))
        canvas.restoreState()

    return on_page


def render(path, story_items, *, running_head: str, title: str,
           subject: str = "") -> None:
    """Build one document from an iterable of flowables."""
    doc = BaseDocTemplate(
        str(path), pagesize=LETTER,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=0.8 * inch,
        title=title,
        author="Houston Strong CPA casework tooling",
        subject=subject,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="main", leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame],
                                       onPage=make_on_page(running_head))])
    doc.build(list(story_items))
