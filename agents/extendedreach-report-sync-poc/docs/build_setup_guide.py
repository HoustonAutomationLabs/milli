#!/usr/bin/env python3
"""Build the printable setup guide.

The guide is generated rather than hand-written so it can be regenerated when
the tool changes and never drifts out of date silently.

    ./.venv/bin/pip install reportlab pypdf     # build-only dependencies
    ./.venv/bin/python docs/build_setup_guide.py

They are deliberately not in requirements.txt: the tool itself does not need
them, and a scheduled job should install as little as possible.

On glyphs: ReportLab's built-in fonts use WinAnsi encoding, so en dashes, em
dashes and curly quotes render correctly (verified, not assumed). Arrows and
check marks do NOT, and a missing glyph renders as a solid black box, so this
file stays clear of them.
"""

from __future__ import annotations

from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path(__file__).resolve().parent / "ExtendedReach-Sync-Setup-Guide.pdf"

from pdf_style import (  # noqa: E402
    S, INK, RULE, CODE_BG, WARN_BG, NOTE_BG, LETTER, MARGIN, CELLB, CELLC,
    ACCENT, BODY, CELL, CODE, CODE_OUT, H1, H2, H3, KICKER, LEAD, MUTED, SMALL,
    callout, code, inch, para, render, step_head, table,
    ParagraphStyle, PageBreak, Paragraph, Spacer, Table, TableStyle, colors,
)

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


def _render(path, toc_pages=None):
    render(path, story(toc_pages),
           running_head="ExtendedReach Report Sync  |  Setup Guide",
           title="ExtendedReach Report Sync - Setup Guide",
           subject="Step-by-step setup for the automated report export")


def build():
    """Two passes: render once to find where each section landed, then render
    again with the real page numbers in the contents table.

    A hand-typed contents page drifts the moment a paragraph is added, and
    silently — the numbers still look plausible. Measuring them removes the
    whole class of error.
    """
    import tempfile

    from pypdf import PdfReader

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        _render(tmp.name)
        reader = PdfReader(tmp.name)
        pages = [(page.extract_text() or "") for page in reader.pages]

    found = {}
    for key, probe in PROBES.items():
        for index, text in enumerate(pages, start=1):
            if index <= 2:           # cover and contents
                continue
            if probe in text:
                found[key] = index
                break

    missing = [k for k in PROBES if k not in found]
    if missing:
        raise SystemExit(f"could not locate section(s) in the rendered PDF: {missing}")

    _render(OUT, found)
    print(f"wrote {OUT} ({len(pages)} pages)")
    for label, title, key in TOC_ENTRIES:
        print(f"   p{found[key]:>2}  {label + ' ' if label else ''}{title}")


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

def story(toc_pages=None):
    toc = toc_pages or {}
    def pg(key):
        return str(toc.get(key, "--"))

    # ================= COVER =================
    yield Spacer(1, 1.1 * inch)
    yield para("SETUP GUIDE", KICKER)
    yield para("ExtendedReach Report Sync",
               S("cover", fontName="Helvetica-Bold", fontSize=27, leading=31,
                 textColor=INK, spaceAfter=10))
    yield para("Automatically download your ExtendedReach reports every day "
               "and file them in Google Drive.",
               S("sub", parent=LEAD, fontSize=13, leading=19, textColor=MUTED))
    yield Spacer(1, 0.3 * inch)

    t = Table([[Paragraph("Written for someone who does not write software. "
                          "Every command is written out in full. Nothing "
                          "assumes prior knowledge.", SMALL)]],
              colWidths=[6.3 * inch])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 2, ACCENT),
                           ("TOPPADDING", (0, 0), (-1, -1), 10),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    yield t

    yield Spacer(1, 0.45 * inch)
    yield para("What you are setting up", H2)
    yield para(
        "Right now, someone signs in to ExtendedReach, opens a report, clicks "
        "<b>Excel</b>, and saves the file. Then does it again for the next "
        "report. Every day. This tool does that same sequence for as many "
        "reports as you configure — nine, or any other number — in one browser "
        "session, on a timer, and puts the results in Google Drive so the "
        "leadership team always has today's numbers.", BODY)
    yield para(
        "It is deliberately boring. It clicks the same buttons a person clicks. "
        "It cannot create, edit, approve, reject, submit or delete anything in "
        "ExtendedReach — that is enforced in the code in three separate "
        "places, not just promised.", BODY)

    yield Spacer(1, 0.16 * inch)
    yield callout(
        "Two things worth knowing before you start",
        "<b>1.</b> Setup takes about an hour, once. After that it runs on its "
        "own.<br/><b>2.</b> The reports contain children's names, dates of "
        "birth and Medicaid numbers. Everything in this guide is designed "
        "around that fact. Nothing shortcuts it.", "warn")

    yield PageBreak()
    yield para("Contents", H1)
    yield Spacer(1, 8)
    yield table(
        ["", "Section", "Page"],
        [[label, title, pg(key)] for label, title, key in TOC_ENTRIES],
        [0.62 * inch, 4.85 * inch, 0.55 * inch])

    yield PageBreak()

    # ================= BEFORE YOU BEGIN =================
    yield para("Before you begin", H1)
    yield para("Five things to have ready. Gather them now and the rest goes "
               "smoothly.", LEAD)

    yield para("1. A Mac that stays on", H3)
    yield para(
        "The tool runs on your Mac, not in the cloud. macOS will not wake a "
        "sleeping Mac to run a scheduled job, so if the laptop is closed at "
        "6 PM, nothing happens that evening. It catches up at the next wake. "
        "If this needs to be dependable, use a Mac that stays awake and "
        "signed in.", BODY)

    yield para("2. Your ExtendedReach login", H3)
    yield para(
        "The username, password and phone or app you use for the "
        "two-factor code. You will type these into the real ExtendedReach "
        "login page yourself, once. You never put them in a file.", BODY)

    yield para("3. The reports you want automated", H3)
    yield para(
        "List them, and know how you reach each one: which menu, which "
        "submenu. You will open each while the tool watches. <b>Start with "
        "one</b>, get it all the way through to Drive, and only then add the "
        "rest — a problem is far easier to find with one report than with "
        "nine.", BODY)

    yield para("4. A Google Drive folder", H3)
    yield para(
        "Create the folder where reports should land. Open it in your browser "
        "and look at the address bar. You need the long jumble of characters "
        "after <font face='Courier'>/folders/</font>:", BODY)
    yield code("https://drive.google.com/drive/folders/1AbCdEf...XyZ",
               "                                      ^^^^^^^^^^^^^^",
               "                                      this part", output=True)
    yield Spacer(1, 6)

    yield para("5. About 60 minutes", H3)
    yield para(
        "Most of it is waiting for downloads and clicking through Google's "
        "permission screens. The parts that need your attention are Steps 5 "
        "and 7. Add roughly five minutes per extra report beyond the first.", BODY)

    yield Spacer(1, 0.2 * inch)
    yield para("How you will type commands", H2)
    yield para(
        "This guide asks you to type things into an app called <b>Terminal</b>. "
        "It comes with every Mac. To open it: press "
        "<b>Command</b> + <b>Space</b>, type <b>Terminal</b>, press "
        "<b>Return</b>.", BODY)
    yield para(
        "A black or white window opens with a blinking cursor. When this guide "
        "shows a shaded box like the one below, type it exactly (or copy and "
        "paste it) and press <b>Return</b>.", BODY)
    yield code("echo hello")
    yield Spacer(1, 4)
    yield para("The window answers:", SMALL)
    yield code("hello", output=True)
    yield Spacer(1, 0.2 * inch)
    yield para("Terminal on its own, or VS Code?", H2)
    yield para(
        "<b>Use VS Code.</b> You will be doing two kinds of work — running "
        "commands, and editing two settings files — and VS Code does both in "
        "one window, with a Terminal built into the bottom of it.", BODY)
    yield para(
        "There is also a specific trap it avoids. TextEdit, the editor that "
        "opens by default on a Mac, substitutes curly quotes for plain ones as "
        "you type. The settings files need plain quotes. The two are almost "
        "impossible to tell apart on screen:", BODY)
    # Shown large and in a proportional face on purpose: at body size, and
    # especially in Courier, the two are genuinely indistinguishable, which is
    # true to life but teaches the reader nothing.
    big = S("big", fontName="Helvetica-Bold", fontSize=17, leading=21,
            textColor=INK)
    lbl = S("lbl", fontName="Helvetica", fontSize=8.5, leading=11,
            textColor=MUTED)
    demo = Table(
        [[Paragraph('"Status"', big), Paragraph('“Status”', big)],
         [Paragraph("plain quotes. correct.", lbl),
          Paragraph("curly quotes. breaks the file.", lbl)]],
        colWidths=[2.4 * inch, 2.4 * inch])
    demo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 2),
        ("LINEBEFORE", (0, 0), (0, -1), 2, ACCENT),
        ("LINEBEFORE", (1, 0), (1, -1), 0.5, RULE),
    ]))
    yield demo
    yield Spacer(1, 8)
    yield para(
        "The tool now spots this and says so in as many words, so it is no "
        "longer a mystery if it happens — but not having it happen is better. "
        "VS Code never substitutes quotes.", BODY)
    yield para("To install it, if you do not have it", H3)
    yield para(
        "Download from <font face='Courier'>code.visualstudio.com</font>, open "
        "the downloaded file, and drag <b>Visual Studio Code</b> into your "
        "Applications folder. Then open it, press <b>Command + Shift + P</b>, "
        "type <b>shell command</b>, and choose <b>Install \'code\' command in "
        "PATH</b>. That last step is what lets you type "
        "<font face='Courier'>code</font> to open a file.", BODY)
    yield para("Opening this project in VS Code", H3)
    yield code("cd ~/Documents/milli/agents/extendedreach-report-sync-poc",
               "code .")
    yield Spacer(1, 6)
    yield para(
        "The <font face='Courier'>.</font> means \"this folder\". VS Code "
        "opens with the project files listed down the left. Press "
        "<b>Control + `</b> (the backtick key, above Tab) to open a Terminal "
        "at the bottom — already in the right folder. Every command in this "
        "guide can be typed there.", BODY)
    yield Spacer(1, 6)
    yield para(
        "If you would rather not install anything, the Terminal app alone "
        "works for everything here. Where this guide says "
        "<font face='Courier'>code somefile</font>, use "
        "<font face='Courier'>open -e somefile</font> instead — and turn off "
        "TextEdit\'s smart quotes first, under <b>Edit -> Substitutions</b>.", BODY)

    yield Spacer(1, 8)
    yield callout(
        "If a command seems to hang",
        "Some commands take a minute or two with no visible progress — "
        "installing the browser in Step 2 is the slow one. That is normal. "
        "You will get your cursor back when it finishes. Do not close the "
        "window.")

    yield PageBreak()

    # ================= HOW IT WORKS =================
    yield para("How it works, in plain English", H1)
    yield para("Nine things happen, in order, every time it runs.", LEAD)

    flow = [
        ("1", "Opens a browser",
         "A real Chrome window, using a saved profile that remembers you are "
         "signed in."),
        ("2", "Checks you are still signed in",
         "It looks for one specific thing on the page that only appears when "
         "signed in. It does not read the page."),
        ("3", "If not signed in, it stops",
         "On a scheduled run it stops and does nothing. It will never type "
         "your password or a two-factor code. Ever."),
        ("4", "Goes to your report",
         "Straight to the address you gave it in Step 5."),
        ("5", "Clicks the export button",
         "The same button you click by hand."),
        ("6", "Saves the file",
         "Into a folder on your Mac, renamed with today's date so files never "
         "overwrite each other."),
        ("7", "Checks the file is real",
         "The important step. See below."),
        ("8", "Uploads it to Google Drive",
         "Only if step 7 passed. Never before."),
        ("9", "Writes down what happened",
         "A log you can read later, with all personal details stripped out."),
    ]
    rows = [[n, Paragraph(f"<b>{t}</b><br/>{d}", CELL)] for n, t, d in flow]
    tb = Table(rows, colWidths=[0.4 * inch, 5.85 * inch])
    tb.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 0), (0, -1), ACCENT),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (0, -1), 11),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#eae7e1")),
    ]))
    yield tb

    yield para("Why step 7 matters more than it sounds", H2)
    yield para(
        "When a website session expires, the site often does not show an "
        "error. It quietly serves a login page instead. Your browser saves "
        "that login page under the filename it expected — so you end up with "
        "a file called something like "
        "<font face='Courier'>report.xlsx</font> that is not a report at all.", BODY)
    yield para(
        "A tool that only checked \"did a file arrive?\" would upload that "
        "happily, every day, and the folder would fill with junk that looks "
        "correct in a file listing. This tool opens the file and confirms it "
        "is a real spreadsheet with the columns you expect. If it is not, "
        "<b>nothing is uploaded</b> and the run is recorded as failed.", BODY)

    yield Spacer(1, 0.1 * inch)
    yield callout(
        "Where your password goes",
        "Into the real ExtendedReach login page, typed by you, once. It is "
        "never stored in a settings file, never in the code, never in a log, "
        "and never sent anywhere. After you sign in the first time, your Mac's "
        "browser profile remembers the session — the same way your browser "
        "keeps you logged in to a website between visits.")

    yield PageBreak()

    # ================= STEP 1 & 2 =================
    yield step_head(1, "Get the software onto your Mac", "5 minutes")
    yield para(
        "The tool lives inside the same project as your dashboard. Open "
        "Terminal and go to that folder. If your project is somewhere other "
        "than your Documents folder, change the path to match.", BODY)
    yield code("cd ~/Documents/milli")
    yield Spacer(1, 8)
    yield para("Now fetch this tool and switch to it:", BODY)
    yield code("git fetch origin",
               "git checkout claude/extendedreach-report-sync-poc-a5jkhn",
               "cd agents/extendedreach-report-sync-poc")
    yield Spacer(1, 8)
    yield para("Check you are in the right place:", BODY)
    yield code("ls")
    yield Spacer(1, 4)
    yield para("You should see these names listed:", SMALL)
    yield code("README.md  config  docs  requirements.txt  scripts  src  tests",
               output=True)

    yield Spacer(1, 0.12 * inch)
    yield callout(
        "If 'git checkout' says the branch is not found",
        "Run <font face='Courier'>git fetch origin</font> on its own first, "
        "wait for it to finish, then try the checkout again. If it still "
        "fails, send me the exact message.")

    yield step_head(2, "Install it", "10-15 minutes, mostly waiting")
    yield para("One command does everything:", BODY)
    yield code("./scripts/install_playwright.sh")
    yield Spacer(1, 8)
    yield para(
        "This sets up a private workspace for the tool, downloads what it "
        "needs, downloads a copy of the Chrome browser for it to drive, and "
        "then runs 99 self-tests. The browser download is the slow part.", BODY)
    yield para("When it finishes you will see:", SMALL)
    yield code("99 passed", "", "Setup complete.", "", "Next:", output=True)
    yield Spacer(1, 8)
    yield para(
        "Those 99 tests passing means the tool's own logic is sound — the "
        "file checking, the naming, the safety rules. It does not yet mean it "
        "works against your portal. That is what Step 7 is for.", BODY)

    yield Spacer(1, 0.12 * inch)
    yield para("The one command to remember", H3)
    yield para(
        "If you ever lose your place in this guide, run this. It tells you "
        "which steps are done and gives you exactly one command to run next.", BODY)
    yield code("./.venv/bin/python -m src.main --doctor")

    yield PageBreak()

    # ================= STEP 3 =================
    yield step_head(3, "Create your settings file", "10 minutes")
    yield para(
        "The tool reads its settings from a file named "
        "<font face='Courier'>.env</font>. Make your own copy of the example:", BODY)
    yield code("cp .env.example .env")
    yield Spacer(1, 8)
    yield para("Then open it for editing:", BODY)
    yield code("code .env")
    yield Spacer(1, 6)
    yield para(
        "(Or <font face='Courier'>open -e .env</font> if you are using "
        "TextEdit rather than VS Code.)", SMALL)
    yield Spacer(1, 10)
    yield para(
        "You will see a long file with explanatory notes. Lines starting with "
        "<font face='Courier'>#</font> are notes — ignore them. You are "
        "looking for lines containing the word <b>TODO</b>. Replace each one.", BODY)

    yield para("What to put where", H3)
    yield table(
        ["Setting", "What to put"],
        [["EXTENDEDREACH_BASE_URL",
          "The web address you sign in to, e.g. "
          "https://youragency.extendedreach.com"],
         ["REPORT_SLUG",
          "A short nickname you choose for this report. Lowercase, use "
          "underscores instead of spaces. Example: past_due_tasks"],
         ["BROWSER_PROFILE_DIR<br/>DOWNLOAD_DIR<br/>LOG_DIR<br/>SCREENSHOT_DIR",
          "Four folders on your Mac. Replace TODO_YOU with your Mac username "
          "and leave the rest. They are created for you."],
         ["GOOGLE_DRIVE_FOLDER_ID",
          "The jumble of characters from your Drive folder address (see "
          "page 2)."],
         ["GOOGLE_CREDENTIALS_FILE<br/>GOOGLE_TOKEN_FILE",
          "Replace TODO_YOU with your Mac username. Step 4 puts a file here."],
         ["EXPECTED_CSV_HEADERS",
          "Leave the TODO for now. You fill this in at Step 6, once you have "
          "seen a real file."]],
        [1.85 * inch, 4.4 * inch])

    yield Spacer(1, 10)
    yield para(
        "Not sure of your Mac username? Run this and use what it prints:", BODY)
    yield code("whoami")
    yield Spacer(1, 10)
    yield para("Save the file (<b>Command</b> + <b>S</b>) and close it.", BODY)

    yield Spacer(1, 0.12 * inch)
    yield callout(
        "Why the folders must be outside the project",
        "Those four folders hold your signed-in browser session and the "
        "downloaded reports — real case data. The project folder is tracked "
        "by version control and gets shared. The tool refuses to start if you "
        "point it at a folder inside the project, so a report can never be "
        "published by accident. If you see that error, that is the safety "
        "working.", "warn")

    yield PageBreak()

    # ================= STEP 4 =================
    yield step_head(4, "Connect Google Drive", "10 minutes")
    yield para(
        "Google needs to know this tool is allowed to put files in your Drive. "
        "This part is all clicking in a web browser.", BODY)

    yield para("A. Create a Google project", H3)
    yield para(
        "Go to <font face='Courier'>console.cloud.google.com</font> and sign "
        "in with the Google account that owns your Drive folder. At the top of "
        "the page there is a project selector. Create a new project and call "
        "it something like <b>ExtendedReach Sync</b>.", BODY)

    yield para("B. Switch on the Drive connection", H3)
    yield para(
        "In the menu on the left, choose <b>APIs and Services</b>, then "
        "<b>Library</b>. Search for <b>Google Drive API</b>. Open it and press "
        "<b>Enable</b>.", BODY)

    yield para("C. Create the credentials", H3)
    yield para(
        "Still under <b>APIs and Services</b>, choose <b>Credentials</b>. "
        "Press <b>Create credentials</b> and pick <b>OAuth client ID</b>.", BODY)
    yield para(
        "If it asks you to configure a consent screen first, do that: choose "
        "<b>Internal</b> if it is offered, give it a name, and enter your own "
        "email in the contact fields. You can skip the optional sections.", BODY)
    yield para(
        "Then, for application type, choose <b>Desktop app</b>. This matters "
        "— the other types will not work. Name it anything. Press "
        "<b>Create</b>, then <b>Download JSON</b>.", BODY)

    yield para("D. Put the file where the tool expects it", H3)
    yield para(
        "You never open this file. You move it into a folder, and that is the "
        "last time you think about it — the software reads it, you do not. If "
        "the Terminal is unfamiliar, "
        "<b>Terminal-Walkthrough.pdf</b> shows these commands as pictures.", BODY)
    yield para(
        "A file lands in your Downloads folder with a long name starting "
        "<font face='Courier'>client_secret</font>. Move and rename it:", BODY)
    yield code("mkdir -p ~/er-sync",
               "mv ~/Downloads/client_secret*.json ~/er-sync/credentials.json")
    yield Spacer(1, 8)
    yield para("Confirm it arrived:", BODY)
    yield code("ls ~/er-sync")
    yield Spacer(1, 4)
    yield para("Should print:", SMALL)
    yield code("credentials.json", output=True)

    yield Spacer(1, 0.12 * inch)
    yield callout(
        "Treat that file like a password",
        "<font face='Courier'>credentials.json</font> lets software act on "
        "your Google account. Do not email it, do not put it in a shared "
        "folder, do not add it to the project folder. It stays in "
        "<font face='Courier'>~/er-sync</font> on your Mac.", "warn")

    yield PageBreak()

    # ================= STEP 5 =================
    yield step_head(5, "Show it your reports", "10 min for the first, 3 each after")
    yield para(
        "The tool does not know where your reports live or what the export "
        "button looks like. This step teaches it, by watching you. You run it "
        "<b>once per report</b> — nine times for nine reports.", BODY)
    yield code("./.venv/bin/python -m src.main --setup-assist")
    yield Spacer(1, 6)
    yield para(
        "It asks for a short name for the report first (your choice — "
        "lowercase, underscores instead of spaces, e.g. "
        "<font face='Courier'>past_due_tasks</font>). Then:", BODY)
    yield Spacer(1, 10)
    yield para("A browser window opens and the Terminal walks you through "
               "three parts.", BODY)

    yield para("Part 1 — Sign in", H3)
    yield para(
        "Sign in to ExtendedReach in that window, exactly as you normally "
        "would, including the two-factor code. Take as long as you need. Then "
        "click back to the Terminal window and press <b>Return</b>.", BODY)
    yield para(
        "It shows you a numbered list of things it found that only appear "
        "when signed in — usually a <b>Sign Out</b> link. Type the number "
        "next to the most obvious one and press <b>Return</b>.", BODY)

    yield para("Part 2 — Open the report", H3)
    yield para(
        "In the browser, navigate to the report you chose, the same way you "
        "always do. If it has filters you want applied every time — a date "
        "range, a program — set them now. Then press <b>Return</b> in the "
        "Terminal.", BODY)
    yield para("It prints the address it captured. Check it looks right.", BODY)

    yield para("Part 3 — Point at the export button", H3)
    yield para(
        "<b>Do not click the export button.</b> Just look at the numbered "
        "list in the Terminal and pick the one that matches it — often "
        "labelled <b>Excel</b>. Type its number and press <b>Return</b>.", BODY)

    yield Spacer(1, 8)
    yield para("Then save what it captured:", BODY)
    yield code("cp config/workflow.draft.json config/workflow.json")
    yield Spacer(1, 10)

    yield para("Now repeat for each remaining report", H3)
    yield para(
        "Run the same command again. It <b>adds</b> the next report and keeps "
        "the ones you have already done — it never starts over. After the "
        "first time it will not ask you to sign in again either, so each extra "
        "report takes two or three minutes.", BODY)
    yield code("./.venv/bin/python -m src.main --setup-assist",
               "cp config/workflow.draft.json config/workflow.json")
    yield Spacer(1, 8)
    yield para("Check what you have so far at any point:", BODY)
    yield code("./.venv/bin/python -m src.main --list-reports")
    yield Spacer(1, 6)
    yield code("  9 report(s) configured",
               "",
               "      slug           columns checked  description",
               "  [x] past_due_tasks 4                Past due case tasks",
               "  [x] open_beds      2                Open beds",
               "  ...",
               "",
               "  9 enabled; these all run on each scheduled run.", output=True)
    yield Spacer(1, 8)
    yield para("And check everything so far makes sense:", BODY)
    yield code("./.venv/bin/python -m src.main --validate-config")
    yield Spacer(1, 6)
    yield para(
        "It either says the configuration is complete, or lists exactly what "
        "is still wrong. Warnings about "
        "<font face='Courier'>expected_csv_headers</font> are expected at this "
        "point — Step 6 fills those in, and they do not block a run.", BODY)

    yield Spacer(1, 0.1 * inch)
    yield callout(
        "If it cannot find the export button",
        "Some portals label it unusually and the automatic scan misses it. "
        "The Terminal will say so and tell you how to find it in Chrome "
        "instead: right-click the button, choose <b>Inspect</b>, then "
        "right-click the highlighted line and choose <b>Copy</b> then "
        "<b>Copy selector</b>. Send me what you copied and I will put it in "
        "the right place.")

    yield PageBreak()

    # ================= STEP 6 =================
    yield step_head(6, "Tell it what a good file looks like", "5 minutes")
    yield para(
        "This is how the tool spots a fake file. You give it the column names "
        "your report actually has; if a download does not have them, it is "
        "rejected and never uploaded.", BODY)

    yield para("A. Download each report by hand, once", H3)
    yield para(
        "In your normal browser, open a report and click the export button. "
        "Open the file that downloads. Repeat for each report — you only ever "
        "do this once per report.", BODY)

    yield para("B. Copy the column headings", H3)
    yield para(
        "Look at the very first row — the headings. Write them out separated "
        "by commas, exactly as they appear, including spaces and symbols:", BODY)
    yield code("Case #,Client Name,Task,Due Date,Status", output=True)
    yield Spacer(1, 8)

    yield para("C. Put them in the workflow file", H3)
    yield para(
        "Each report has its own columns, so each report gets its own list. "
        "Open the workflow file:", BODY)
    yield code("code config/workflow.json")
    yield Spacer(1, 8)
    yield para(
        "Find your report by its short name, and fill in the "
        "<font face='Courier'>expected_csv_headers</font> list inside its "
        "<font face='Courier'>validation</font> section. It looks like this:", BODY)
    yield code('"past_due_tasks": {',
               '  "enabled": true,',
               '  "validation": {',
               '    "expected_csv_headers": ["Case #", "Task", "Due Date", "Status"]',
               '  }',
               '}', output=True)
    yield Spacer(1, 8)
    yield para(
        "Each name in double quotes, commas between them. Do this for every "
        "report. Leave the list empty — <font face='Courier'>[]</font> — for "
        "any report you do not want column-checked; it is still checked for "
        "size and file type.", BODY)

    yield Spacer(1, 6)
    yield para("Now confirm:", BODY)
    yield code("./.venv/bin/python -m src.main --validate-config")
    yield Spacer(1, 6)
    yield para("You want to see:", SMALL)
    yield code("Configuration is complete and internally consistent.", output=True)

    yield Spacer(1, 0.14 * inch)
    yield callout(
        "You do not need every column",
        "List the ones that should always be there. Extra columns in the file "
        "are fine — reports gain columns over time and that should not break "
        "anything. Missing ones are what get caught. Pick four or five "
        "distinctive headings rather than all forty.")

    yield Spacer(1, 0.14 * inch)
    yield para("A useful check that touches nothing", H3)
    yield para(
        "This makes up fake files and proves the checking works, without "
        "going near ExtendedReach or Drive:", BODY)
    yield code("./.venv/bin/python -m src.main --test-download-fixture")
    yield Spacer(1, 6)
    yield para(
        "Six samples are tested. Four should pass. <b>Two should fail</b> — "
        "a cut-off file and a login page disguised as a spreadsheet. Those two "
        "failures are the point: they are what protects your Drive folder.", BODY)

    yield PageBreak()

    # ================= STEP 7 =================
    yield step_head(7, "Test run — nothing gets uploaded", "10 minutes")
    yield para(
        "This is the real test: the first time the tool meets your actual "
        "portal. It downloads and checks a report but <b>stops before "
        "uploading</b>, so there is nothing to undo.", BODY)
    yield code("./scripts/run_once.sh --dry-run")
    yield Spacer(1, 10)
    yield para(
        "A browser window opens. Because you signed in during Step 5, it "
        "should already know you. If it asks you to sign in again, do so — it "
        "waits.", BODY)
    yield para("Watch it navigate, click export, and save the file. Then:", BODY)
    yield para(
        "It works through every report in one browser session, then prints a "
        "line per report:", BODY)
    yield code("  past_due_tasks  success",
               "  open_beds       success",
               "  next_court      success",
               "  ...",
               "  9 uploaded, 0 already there, 0 failed of 9 report(s)",
               output=True)
    yield Spacer(1, 8)
    yield para(
        "If one report fails, the others still run. That is deliberate — a "
        "single mislabelled button should not cost you the other eight.", BODY)

    yield Spacer(1, 10)
    yield para("Now open the files yourself and look at them", H3)
    yield para("This is the part worth doing carefully.", BODY)
    yield code("open ~/er-sync/downloads")
    yield Spacer(1, 8)
    yield para("Check three things:", BODY)
    yield para(
        "Check each one. This is tedious with nine reports and it is the only "
        "time you have to do it.", SMALL)
    yield table(
        ["Check", "Why"],
        [["Is it the right report?",
          "Confirms it went to the right page, not a neighbouring one. With "
          "several reports, the failure to watch for is two files that are "
          "actually the same export."],
         ["Are the filters applied?",
          "If you set a date range in Step 5, confirm the file reflects it."],
         ["Does the row count look sane?",
          "A report with 3 rows when you expect 900 means a filter is wrong."]],
        [1.85 * inch, 4.4 * inch])

    yield Spacer(1, 0.14 * inch)
    yield callout(
        "If this step fails, that is normal and useful",
        "This is the first contact between the tool and your portal. Common "
        "outcomes: the export button was mislabelled, a column name does not "
        "match, or the page layout differs from what was captured. The tool "
        "tells you which, in plain words, and stops safely. Send me the "
        "message and the run id and I will fix it — this is the part I could "
        "not test in advance because I have never seen your portal.")

    yield PageBreak()

    # ================= STEP 8 =================
    yield step_head(8, "The first real run", "5 minutes")
    yield para(
        "Same as the test, but it uploads. Only do this once you are happy "
        "with the file you opened in Step 7.", BODY)
    yield code("./scripts/run_once.sh")
    yield Spacer(1, 10)
    yield para(
        "The first time only, a browser tab opens asking you to let the tool "
        "use Google Drive. Sign in with the account that owns the folder and "
        "approve it.", BODY)

    yield Spacer(1, 6)
    yield callout(
        "If Google warns the app is not verified",
        "You will likely see a screen saying the app is not verified. That is "
        "expected — you built it, and Google only verifies apps that are "
        "published publicly. Choose <b>Advanced</b>, then <b>Go to ... "
        "(unsafe)</b>. It is your own project, approved by you, and access is "
        "limited to files this tool creates.")

    yield Spacer(1, 10)
    yield para("You should end with a Drive file id:", BODY)
    yield code("status     success",
               "file       extendedreach_past_due_tasks_2026-08-26_183012.csv",
               "drive id   1XyZ...", output=True)
    yield Spacer(1, 10)
    yield para("Open your Drive folder in a browser. The file should be there.", BODY)

    yield para("Run it twice on purpose", H3)
    yield para("Run the exact same command again:", BODY)
    yield code("./scripts/run_once.sh")
    yield Spacer(1, 6)
    yield para("This time it should say:", SMALL)
    yield code("status     skipped", "drive id   1XyZ...", output=True)
    yield Spacer(1, 8)
    yield para(
        "It recognised that today's report is already in the folder and "
        "declined to upload a second copy. This is why the schedule can safely "
        "run six times a day without cluttering the folder — and why a manual "
        "re-run after a problem will not create duplicates.", BODY)

    yield PageBreak()

    # ================= STEP 9 =================
    yield step_head(9, "Turn on the daily schedule", "5 minutes")
    yield para("Pick one of these two.", BODY)

    yield para("Option A — once a day at 6 PM", H3)
    yield code("./scripts/install_schedule.sh daily")
    yield Spacer(1, 6)
    yield para("Simple. One attempt each evening.", SMALL)

    yield para("Option B — every two hours, weekdays (recommended)", H3)
    yield code("./scripts/install_schedule.sh business-hours")
    yield Spacer(1, 6)
    yield para(
        "Tries at 8, 10, 12, 2, 4 and 6, Monday to Friday. Because of the "
        "duplicate check you saw in Step 8, you still get <b>one file per "
        "day</b> — the other five runs notice it is already there and stop. "
        "The benefit is six chances to catch a moment when your Mac is awake "
        "and the session is valid, instead of one.", BODY)

    yield Spacer(1, 10)
    yield para("Confirm it is registered:", BODY)
    yield code("launchctl list | grep extendedreach")
    yield Spacer(1, 8)
    yield para("Test it without waiting for the clock:", BODY)
    yield code("launchctl start com.agency.extendedreach-report-sync")
    yield Spacer(1, 6)
    yield para("Wait a minute, then check what happened:", BODY)
    yield code("./.venv/bin/python -m src.main --status")

    yield Spacer(1, 0.14 * inch)
    yield para("To turn it off again, at any time", H3)
    yield code("./scripts/install_schedule.sh --uninstall")
    yield Spacer(1, 6)
    yield para(
        "This only stops the timer. Your downloads, logs and Drive files are "
        "untouched, and you can still run it by hand.", SMALL)

    yield Spacer(1, 0.14 * inch)
    yield callout(
        "It refuses to schedule something that has never worked",
        "If you skipped ahead and Step 8 never succeeded, this command will "
        "stop and tell you so. A timer on something broken just produces a "
        "failure every evening. Finish Step 8 first.")

    yield PageBreak()

    # ================= WEEKLY =================
    yield para("Your weekly two-minute check", H1)
    yield para(
        "Automation fails quietly. This is the habit that catches it.", LEAD)
    yield code("cd ~/Documents/milli/agents/extendedreach-report-sync-poc",
               "./.venv/bin/python -m src.main --status")

    yield Spacer(1, 12)
    yield para("What you might see", H2)

    yield para("All good", H3)
    yield code("  report          when         status     detail",
               "  past_due_tasks  08-27 18:00  success    1XyZ...",
               "  open_beds       08-27 18:00  success    1AbC...",
               "  ...",
               "",
               "  All 9 report(s) are up to date.", output=True)
    yield para("Nothing to do.", SMALL)

    yield para("One report broken, the rest fine", H3)
    yield code("  ACTION NEEDED: 1 report(s) failing on the last run:",
               "      open_beds     portal_structure_changed",
               "  The other 8 are fine, so this is that report's own problem,",
               "  not the session.", output=True)
    yield para(
        "That last line is the one that matters. If one report fails and the "
        "others succeed, the sign-in is fine and something changed on that "
        "one report's page — send me the report name and the category. If "
        "<b>every</b> report fails at once, it is almost always the session, "
        "not nine broken pages.", BODY)

    yield para("Needs you — the most common one", H3)
    yield code("  ACTION NEEDED: the portal session has expired.",
               "  One headed run signs it back in:  ./scripts/run_once.sh",
               "  Until then every report is stopped, uploading nothing.",
               output=True)
    yield para(
        "Your ExtendedReach session lapsed. This is expected every so often — "
        "how often depends on your agency's settings. The tool correctly "
        "refused to do anything about it, because the alternative would be "
        "automating your login. Run the command it names, sign in, and the "
        "schedule picks up again on its own.", BODY)

    yield para("Something broke", H3)
    yield code("2026-08-26 18:00:00  failed        portal_structure_changed",
               output=True)
    yield para(
        "Usually means ExtendedReach changed its page layout. Send me the "
        "category shown (the part after 'failed') and I will adjust it.", BODY)

    yield Spacer(1, 0.16 * inch)
    yield callout(
        "Why not just look at the Drive folder?",
        "Because an empty folder cannot tell you the difference between "
        "\"nothing needed uploading\" and \"it has been failing for six days\". "
        "The status command can. Two minutes on a Monday is the whole "
        "maintenance burden.", "warn")

    yield Spacer(1, 0.16 * inch)
    yield para("Lost your place at any point?", H2)
    yield code("./.venv/bin/python -m src.main --doctor")
    yield para(
        "Shows the nine setup steps, ticks off what is done, and gives you one "
        "command to run next.", SMALL)

    yield PageBreak()

    # ================= TROUBLESHOOTING =================
    yield para("When something goes wrong", H1)
    yield para(
        "Every run ends with a number. Zero means fine. Anything else has a "
        "specific meaning.", LEAD)

    yield table(
        ["Code", "Meaning", "What to do"],
        [["0", "Worked, or correctly skipped a duplicate", "Nothing"],
         ["1", "Something unexpected",
          "Run --status and send me what it says"],
         ["2", "Settings incomplete",
          "Run --validate-config; it lists what is missing"],
         ["3", "Someone must sign in",
          "Run ./scripts/run_once.sh and sign in. Most common one."],
         ["4", "The file failed its checks",
          "Often the session expired mid-run and a login page was saved. "
          "Nothing was uploaded, which is correct."],
         ["5", "Could not reach or export the report",
          "Usually the portal layout changed. Send me the category."],
         ["6", "Google Drive refused the upload",
          "Check the folder id, and that the Google account is right"],
         ["7", "Another run was already going",
          "Nothing. The safety worked."]],
        [0.55 * inch, 2.15 * inch, 3.55 * inch])

    yield Spacer(1, 0.2 * inch)
    yield para("Specific messages", H2)

    yield para("\"resolves inside the git repository\"", H3)
    yield para(
        "One of your four folder settings points inside the project folder. "
        "Move it to <font face='Courier'>~/er-sync/...</font> instead. This "
        "guard exists so a downloaded report can never be published by "
        "accident.", BODY)

    yield para("\"chromium did not start\"", H3)
    yield para("Re-run the installer:", BODY)
    yield code("./scripts/install_playwright.sh")

    yield para("\"is not valid JSON\"", H3)
    yield para(
        "Something in <font face='Courier'>config/workflow.json</font> is "
        "malformed. The message names the line and, where it can, the actual "
        "cause — most often curly quotes substituted by a text editor, which "
        "look identical to plain ones on screen. Fix what it names, or "
        "re-open the file in VS Code, which does not substitute them.", BODY)

    yield para("\"csv_headers_missing\"", H3)
    yield para(
        "The file arrived but a column you listed in Step 6 was not in it. "
        "Either the report changed, or a heading was typed slightly wrong. "
        "Download the report by hand and compare the first row against your "
        "<font face='Courier'>EXPECTED_CSV_HEADERS</font> line.", BODY)

    yield para("\"drive_upload_failed\"", H3)
    yield para(
        "If this mentions a 403, the Drive folder was not created by this "
        "tool and Google will not let it write there under the limited "
        "permission it asks for. Easiest fix: let the tool create its own "
        "subfolder, and use that folder's id instead. Tell me and I will set "
        "it up.", BODY)

    yield para("The schedule runs but nothing appears", H3)
    yield para("Check, in this order:", BODY)
    yield table(
        ["Check", "How"],
        [["Was the Mac awake at that hour?",
          "macOS will not wake a sleeping Mac for a scheduled job."],
         ["Is the job registered?",
          "launchctl list | grep extendedreach"],
         ["What do the runs say?",
          "./.venv/bin/python -m src.main --status"],
         ["Did it ever work by hand?",
          "./scripts/run_once.sh"]],
        [2.3 * inch, 3.95 * inch])

    yield PageBreak()

    # ================= WHAT IT NEVER DOES =================
    yield para("What this tool will never do", H1)
    yield para(
        "These are enforced in the code, not left to good intentions. Worth "
        "knowing if leadership asks.", LEAD)

    yield table(
        ["It will never...", "How that is guaranteed"],
        [["Change anything in ExtendedReach",
          "It can only perform actions from a fixed read-only list, and it "
          "refuses to visit any address containing words like delete, submit "
          "or approve."],
         ["Type your password or two-factor code",
          "There is no place in the settings to put them. A check confirms no "
          "such field exists anywhere in the code."],
         ["Type a person's name into a search box",
          "Filter values must match a strict pattern that excludes free text, "
          "apostrophes and commas — which rules out names."],
         ["Upload a file it has not checked",
          "There is no path through the code from download to upload that "
          "skips validation."],
         ["Put case details in a log",
          "Logs are scrubbed automatically, and errors are recorded as fixed "
          "category names rather than messages, because error messages from a "
          "browser often quote the page."],
         ["Screenshot a report page",
          "Screenshots are off unless you turn them on, and even then they "
          "are only taken on a login or error page — never one that could "
          "show a child's record."],
         ["Send a screenshot to Drive",
          "Only the validated report file is ever uploaded."]],
        [1.95 * inch, 4.3 * inch])

    yield Spacer(1, 0.2 * inch)
    yield para("Two things to keep an eye on", H2)
    yield para(
        "<b>The Google account.</b> Files land in the Drive you chose. Make "
        "sure that account is the right one for records of this kind, and that "
        "the folder is shared only with people who should see them.", BODY)
    yield para(
        "<b>The four folders on your Mac.</b> "
        "<font face='Courier'>~/er-sync/downloads</font> accumulates real "
        "reports over time. They are as sensitive as anything in "
        "ExtendedReach. Keep the Mac locked, encrypted (FileVault) and "
        "backed up somewhere appropriate — or clear the folder periodically "
        "once files are safely in Drive.", BODY)

    yield PageBreak()

    # ================= GLOSSARY =================
    yield para("Words this guide uses", H1)
    yield Spacer(1, 4)
    yield table(
        ["Word", "What it means here"],
        [["Terminal",
          "The Mac app where you type commands. Command + Space, type "
          "Terminal, press Return."],
         ["Command",
          "A line you type into Terminal and run by pressing Return."],
         ["Repository (repo)",
          "The project folder, with a history of every change. Yours is "
          "called milli."],
         ["Branch",
          "A named version of the project. This tool lives on a branch so it "
          "does not disturb the dashboard."],
         [".env file",
          "Your private settings. Never shared, never uploaded. The dot at "
          "the start makes it hidden in Finder."],
         ["Selector",
          "A precise way of pointing at one thing on a web page — like a "
          "seat number in a theatre. Step 5 captures these for you."],
         ["MFA / two-factor",
          "The extra code from your phone or an app when you sign in. This "
          "tool never handles it; you always type it yourself."],
         ["CSV / XLSX",
          "Two spreadsheet file types. CSV is plain text; XLSX is Excel. "
          "Some reports come as one, some the other."],
         ["Dry run",
          "A rehearsal. Everything happens except the upload."],
         ["Run key",
          "An invisible label of report plus date, attached to each upload. "
          "It is how the tool recognises today's file is already there."],
         ["Exit code",
          "The number a run ends with. 0 is good; see page 13."],
         ["launchd",
          "The part of macOS that runs things on a schedule. Step 9 sets it "
          "up for you."],
         ["Headed / headless",
          "Headed means you can see the browser window. Headless means it "
          "runs invisibly, which is how the schedule runs it."]],
        [1.5 * inch, 4.75 * inch])

    yield PageBreak()

    # ================= QUICK REFERENCE =================
    yield para("One-page command reference", H1)
    yield para(
        "Every command starts by going to the project folder. Adjust the path "
        "if yours differs.", LEAD)
    yield code("cd ~/Documents/milli/agents/extendedreach-report-sync-poc")

    yield para("Day to day", H2)
    yield table(
        ["Command", "What it does"],
        [["./.venv/bin/python -m src.main --status",
          "Latest run of every report. Says if anything needs you. "
          "<b>Run weekly.</b>"],
         ["./.venv/bin/python -m src.main --list-reports",
          "Every report configured, and whether it is switched on"],
         ["./.venv/bin/python -m src.main --doctor",
          "Where am I in setup, and what is the one next command"],
         ["./scripts/run_once.sh",
          "Run every enabled report now, for real"],
         ["./scripts/run_once.sh --report open_beds",
          "Run just one report"],
         ["./scripts/run_once.sh --dry-run",
          "Run it now, but do not upload"]],
        [3.0 * inch, 3.25 * inch])

    yield para("Setup", H2)
    yield table(
        ["Command", "What it does"],
        [["./scripts/install_playwright.sh",
          "Install everything (Step 2)"],
         ["cp .env.example .env",
          "Create your settings file (Step 3)"],
         ["code .env",
          "Edit your settings (open -e .env without VS Code)"],
         ["code .",
          "Open the whole project in VS Code"],
         ["./.venv/bin/python -m src.main --setup-assist",
          "Add ONE report. Run again for each (Step 5)"],
         ["./.venv/bin/python -m src.main --validate-config",
          "Check the settings make sense"],
         ["./.venv/bin/python -m src.main --test-download-fixture",
          "Prove the file checking works, offline"]],
        [3.0 * inch, 3.25 * inch])

    yield para("The schedule", H2)
    yield table(
        ["Command", "What it does"],
        [["./scripts/install_schedule.sh daily",
          "Run every day at 6 PM"],
         ["./scripts/install_schedule.sh business-hours",
          "Every two hours, weekdays (recommended)"],
         ["./scripts/install_schedule.sh --uninstall",
          "Stop the schedule"],
         ["launchctl list | grep extendedreach",
          "Is the schedule registered?"],
         ["launchctl start com.agency.extendedreach-report-sync",
          "Run the scheduled job right now"]],
        [3.0 * inch, 3.25 * inch])

    yield Spacer(1, 0.25 * inch)
    yield callout(
        "If you only remember one command",
        "<font face='Courier'><b>./.venv/bin/python -m src.main --doctor</b></font>"
        "<br/>It always tells you where you are and what to do next.")

    yield Spacer(1, 0.3 * inch)
    yield para(
        "This guide is generated from the project itself and regenerated when "
        "the tool changes. If a command here does not match what you see on "
        "screen, trust the screen and tell me.", SMALL)


if __name__ == "__main__":
    build()
