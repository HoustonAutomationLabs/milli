#!/usr/bin/env python3
"""Build the Claude-in-Chrome prompt sheet.

A companion to the setup guide, covering only the two setup tasks that involve
no case data: the Google Cloud project and the Drive folders.

    ./.venv/bin/python docs/build_chrome_prompts.py

Shares its look with the setup guide via docs/pdf_style.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path(__file__).resolve().parent / "Claude-in-Chrome-Prompts.pdf"

from pdf_style import (  # noqa: E402
    ACCENT, BODY, CELL, CELLB, CODE_BG, H1, H2, H3, INK, KICKER, LEAD, MUTED,
    RULE, S, SMALL, Spacer, PageBreak, Paragraph, Table, TableStyle,
    callout, code, colors, inch, para, render, table,
)

PROMPT_STYLE = S("prompt", fontName="Helvetica-Oblique", fontSize=9.5,
                 leading=14, textColor=colors.HexColor("#26221d"), spaceAfter=0)


def prompt(*lines):
    """A block of text to paste to Claude, styled apart from shell commands."""
    rows = [[Paragraph(line, PROMPT_STYLE)] for line in lines]
    t = Table(rows, colWidths=[6.3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f4f2")),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 2),
        ("LINEBEFORE", (0, 0), (0, -1), 2, colors.HexColor("#5f8f70")),
    ]))
    return t


def task(number, title):
    left = Paragraph(f"TASK {number}", S("tn", fontName="Helvetica-Bold",
                                         fontSize=8.5, leading=11,
                                         textColor=colors.white))
    badge = Table([[left]], colWidths=[0.72 * inch])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    t = Table([[badge, Paragraph(title, S("tt", fontName="Helvetica-Bold",
                                          fontSize=12.5, leading=16,
                                          textColor=INK))]],
              colWidths=[0.82 * inch, 5.6 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.8, RULE),
    ]))
    return t


def story():
    # ================= COVER =================
    yield Spacer(1, 0.9 * inch)
    yield para("COMPANION SHEET", KICKER)
    yield para("Claude in Chrome",
               S("cover", fontName="Helvetica-Bold", fontSize=27, leading=31,
                 textColor=INK, spaceAfter=10))
    yield para("Prompts for the two setup tasks that involve no case data: "
               "the Google Cloud project, and the Drive folders.",
               S("sub", parent=LEAD, fontSize=13, leading=19, textColor=MUTED))

    yield Spacer(1, 0.3 * inch)
    yield callout(
        "The one rule that matters",
        "<b>Never let Claude in Chrome see ExtendedReach.</b> Not the login "
        "page, not a report, not a downloaded file. Those pages are children's "
        "records, and an assistant that reads a page to decide what to click "
        "would be reading them. Close those tabs, or switch the extension off, "
        "before you open the portal.<br/><br/>"
        "Google Cloud Console and an empty Drive folder contain no case data. "
        "That is the whole difference, and it is why these two tasks are safe "
        "and the rest are not.", "warn")

    yield Spacer(1, 0.25 * inch)
    yield para("How to use this sheet", H2)
    yield para(
        "Each task below has text in a green box. Paste it to Claude in Chrome "
        "and let it work. It will ask permission before each action it takes "
        "— read what it is about to do before approving. You are the one "
        "accountable for the result, and approving without reading is how "
        "people end up with the wrong project or a folder shared too widely.", BODY)
    yield para(
        "After each task there is a <b>Check it yourself</b> box. Do those. "
        "They take seconds and they are the difference between believing the "
        "task is done and knowing it.", BODY)

    yield Spacer(1, 0.2 * inch)
    yield para("Before you start", H2)
    yield table(
        ["", ""],
        [["Extension installed",
          "Claude in Chrome is a browser extension. If you do not have it, "
          "check what is available on your plan at claude.ai — availability "
          "and the exact name have changed over time. Everything in this "
          "sheet can be done by hand instead; the setup guide has the manual "
          "click paths."],
         ["Signed in to Google",
          "In the SAME Chrome profile, signed in as the account that will own "
          "the Drive folder. If you have several Google accounts, this is the "
          "single most common thing to get wrong."],
         ["Portal tabs closed",
          "No ExtendedReach tab open anywhere in this window."]],
        [1.5 * inch, 4.75 * inch])

    yield PageBreak()

    # ================= TASK 1 =================
    yield task(1, "Create the Google Cloud project")
    yield para(
        "Open <font face='Courier'>console.cloud.google.com</font> in a tab "
        "first, then paste this.", BODY)
    yield prompt(
        "I'm setting up a small internal tool that needs to upload files to my "
        "own Google Drive. Please help me in the Google Cloud Console:",
        "",
        "1. Create a new project named \"ExtendedReach Sync\".",
        "2. Switch to that project once it exists.",
        "3. Enable the Google Drive API for it.",
        "",
        "Tell me each thing you're about to do before you do it, and stop and "
        "ask me if a screen looks different from what you expected. Don't "
        "enable any other APIs, and don't change billing or IAM settings.")

    yield Spacer(1, 10)
    yield callout(
        "Check it yourself",
        "Look at the project selector at the top of the page. It should say "
        "<b>ExtendedReach Sync</b>. Then go to <b>APIs and Services -> Enabled "
        "APIs and services</b> and confirm <b>Google Drive API</b> is listed. "
        "If a different project is selected, everything after this lands in "
        "the wrong place.")

    # ================= TASK 2 =================
    yield task(2, "Set up the consent screen")
    yield para(
        "Google requires this before it will issue credentials. It is a form, "
        "and the wording changes; let Claude find the current version.", BODY)
    yield prompt(
        "In this same Google Cloud project, please configure the OAuth consent "
        "screen so I can create credentials:",
        "",
        "- Choose \"Internal\" if that option is available. If only "
        "\"External\" is offered, tell me before selecting it — I want to know.",
        "- App name: \"ExtendedReach Sync\"",
        "- Use my own email address for the support and developer contact "
        "fields.",
        "- Skip anything optional. Don't add scopes or test users unless a "
        "required field forces it, and tell me if it does.",
        "",
        "Show me each screen before submitting it.")

    yield Spacer(1, 10)
    yield callout(
        "Why 'Internal' versus 'External' matters",
        "<b>Internal</b> means only people in your Google Workspace "
        "organisation can authorise the app. That is what you want. "
        "<b>External</b> is offered on personal Google accounts and means the "
        "app is, in principle, open to any Google account — you then have to "
        "add yourself as a test user. It still works, but it is worth knowing "
        "which one you ended up on, which is why the prompt asks Claude to "
        "tell you.")

    yield PageBreak()

    # ================= TASK 3 =================
    yield task(3, "Create the credentials file")
    yield para(
        "This is the step with a wrong answer that looks right, so the prompt "
        "is specific about it.", BODY)
    yield prompt(
        "Now please create an OAuth client ID in this project:",
        "",
        "- Go to APIs and Services, then Credentials, then Create credentials, "
        "then OAuth client ID.",
        "- For Application type, choose \"Desktop app\". This is important — "
        "\"Web application\" will not work for what I'm doing. If \"Desktop "
        "app\" isn't in the list, stop and tell me rather than picking "
        "something close.",
        "- Name it \"ExtendedReach Sync desktop client\".",
        "- Create it, then download the JSON credentials file.",
        "",
        "Tell me where the file was saved. Do not open it, paste its contents "
        "into the chat, or share it anywhere.")

    yield Spacer(1, 10)
    yield callout(
        "Then move it yourself, in Terminal",
        "The downloaded file is a credential. Put it where the tool expects "
        "it, outside the project folder:")
    yield Spacer(1, 6)
    yield code("mkdir -p ~/er-sync",
               "mv ~/Downloads/client_secret*.json ~/er-sync/credentials.json",
               "ls ~/er-sync")
    yield Spacer(1, 6)
    yield para(
        "Do this part by hand rather than asking Claude to. A file that lets "
        "software act on your Google account is worth moving deliberately.", SMALL)

    yield Spacer(1, 0.14 * inch)
    yield callout(
        "Check it yourself",
        "<font face='Courier'>ls ~/er-sync</font> should print "
        "<font face='Courier'>credentials.json</font>. Back in the Console, "
        "under Credentials, the new client should be listed with type "
        "<b>Desktop</b>. If it says Web application, delete it and redo this "
        "task — it will fail later with a confusing error otherwise.")

    yield PageBreak()

    # ================= TASK 4 =================
    yield task(4, "Create the Drive folders")
    yield para(
        "One parent folder, and a subfolder per report if you want them kept "
        "apart. Open <font face='Courier'>drive.google.com</font> first.", BODY)
    yield para(
        "Edit the report names in the list below to match yours before "
        "pasting. Nine are shown as an example.", SMALL)
    yield prompt(
        "In Google Drive, please create this folder structure for me:",
        "",
        "A top-level folder called \"ExtendedReach Reports\", containing these "
        "subfolders:",
        "",
        "Past Due Tasks, Past Due Home Tasks, Tasks In Process, Open Cases, "
        "Caseload by Worker, On Time by Program, Open Beds, Next Court Date, "
        "Staff Expirations",
        "",
        "Create them empty. Don't change sharing on anything yet — I'll do "
        "that separately. Tell me when they exist.")

    yield Spacer(1, 10)
    yield para("If you would rather keep everything in one folder", H3)
    yield para(
        "Simpler, and the filenames already say which report and which date "
        "they came from. In that case just create the parent folder and skip "
        "the subfolders — the tool puts everything in one place by default.", BODY)

    yield Spacer(1, 0.14 * inch)
    yield para("Collect the folder IDs", H2)
    yield para(
        "The tool identifies a folder by the jumble of characters in its web "
        "address, not by its name. You need one per folder you will use.", BODY)
    yield prompt(
        "Please open each of those folders in turn and give me a plain list "
        "of the folder name and its folder ID — the part of the address after "
        "/folders/. Just the list, nothing else.")

    yield Spacer(1, 10)
    yield para("You will get something like:", SMALL)
    yield code("Past Due Tasks       1AbCdEfGhIjKlMnOpQrStUvWxYz",
               "Open Beds            1ZyXwVuTsRqPoNmLkJiHgFeDcBa",
               "...", output=True)
    yield Spacer(1, 10)
    yield para(
        "Keep that list. The parent folder's id goes in "
        "<font face='Courier'>GOOGLE_DRIVE_FOLDER_ID</font> in your "
        "<font face='Courier'>.env</font>. Per-report folders are optional — "
        "the setup guide's multiple-reports section covers wiring those up.", BODY)

    yield PageBreak()

    # ================= TASK 5 =================
    yield task(5, "Share the folders — carefully")
    yield para(
        "This is the one task where a mistake has real consequences, so the "
        "prompt is deliberately narrow and the check afterwards matters most.", BODY)

    yield callout(
        "Never make these folders link-shareable",
        "\"Anyone with the link\" on a folder holding children's names, dates "
        "of birth and Medicaid numbers means anyone who ever receives that "
        "link — forwarded, pasted into a ticket, left in an email thread — can "
        "open it. Share with <b>named people only</b>. The prompt below says "
        "so explicitly; check it anyway.", "warn")

    yield Spacer(1, 10)
    yield para(
        "Replace the names and addresses with the real people before pasting.", SMALL)
    yield prompt(
        "Please share the \"ExtendedReach Reports\" folder with these specific "
        "people:",
        "",
        "- firstname.lastname@example.org — Viewer",
        "- firstname.lastname@example.org — Viewer",
        "",
        "Important: share with these named individuals only. Do NOT set it to "
        "\"Anyone with the link\", do not make it public, and do not change "
        "the general access setting at all. Turn OFF notification emails if "
        "that option is offered. Show me the sharing dialog before you "
        "confirm, so I can check it.")

    yield Spacer(1, 0.16 * inch)
    yield callout(
        "Check it yourself — do not skip this one",
        "Right-click the folder, choose <b>Share</b>, and read the "
        "<b>General access</b> line at the bottom. It must say "
        "<b>Restricted</b>. If it says \"Anyone with the link\", change it to "
        "Restricted now. Then read the list of people above it and confirm "
        "every name belongs there.", "warn")

    yield Spacer(1, 0.16 * inch)
    yield para("Viewer, not Editor", H3)
    yield para(
        "People who read the reports need <b>Viewer</b>. Editor lets them "
        "delete files, including ones the tool has already uploaded. Only the "
        "account the tool itself signs in as needs to write.", BODY)

    yield PageBreak()

    # ================= LIMITS =================
    yield para("What not to ask it", H1)
    yield para(
        "The boundary is simple: anything that can see a child's record, or "
        "can change something in ExtendedReach.", LEAD)

    yield table(
        ["Do not ask Claude in Chrome to...", "Why"],
        [["Open, read or navigate ExtendedReach",
          "The pages are children's records. An assistant that reads a page "
          "to decide what to click is reading them, and they would leave your "
          "agency's control."],
         ["Capture the report selectors",
          "That means being on a report page. The tool's own "
          "<font face='Courier'>--setup-assist</font> does this without any "
          "AI reading the page — it matches text patterns and you choose from "
          "a numbered list."],
         ["Open a downloaded report",
          "Same data, different window."],
         ["Run the export \"just this once\"",
          "ExtendedReach has approve, reject and delete buttons on the same "
          "screens as export. The Python tool cannot press them by "
          "construction. An assistant reading a page has no such floor."],
         ["Fix the tool's settings files",
          "<font face='Courier'>.env</font> holds the Drive folder and file "
          "paths; edit it yourself. "
          "<font face='Courier'>--validate-config</font> tells you exactly "
          "what is wrong."],
         ["Handle credentials.json",
          "Move it in Terminal. It is a credential."]],
        [2.35 * inch, 3.9 * inch])

    yield Spacer(1, 0.2 * inch)
    yield para("Things it is genuinely useful for", H2)
    yield table(
        ["Ask it to...", ""],
        [["Explain an error message",
          "Paste the text of a Terminal or Google error. Nothing sensitive in "
          "those."],
         ["Find the current Google documentation",
          "The Console's layout changes; public docs are fair game."],
         ["Re-do any task on this sheet",
          "If something got misconfigured, the same prompts work again."],
         ["Check a folder's sharing settings",
          "Reading the sharing dialog of a folder is fine — that is settings, "
          "not contents. Do not ask it to open the files inside."]],
        [2.35 * inch, 3.9 * inch])

    yield Spacer(1, 0.25 * inch)
    yield para("One last thing", H2)
    yield para(
        "Everything on this sheet can be done by hand in about fifteen "
        "minutes, and the setup guide has the manual click path for each. If "
        "an assistant gets confused by a screen that has changed, doing it "
        "yourself is not a fallback — it is just the other way of doing it.", BODY)


def build():
    render(OUT, story(),
           running_head="ExtendedReach Report Sync  |  Claude in Chrome",
           title="Claude in Chrome - Prompt Sheet",
           subject="Prompts for the Google Cloud and Drive setup tasks")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
