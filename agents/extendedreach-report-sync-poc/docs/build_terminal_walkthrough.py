#!/usr/bin/env python3
"""Build the illustrated Terminal walkthrough.

For the reader who has never used a terminal. Every command is shown as a
picture of the window, with the real output captured by running it.

    ./.venv/bin/python docs/build_terminal_walkthrough.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path(__file__).resolve().parent / "Terminal-Walkthrough.pdf"

from pdf_style import (  # noqa: E402
    ACCENT, BODY, CELL, CELLB, CODE_BG, H1, H2, H3, INK, KICKER, LEAD, MUTED,
    RULE, S, SMALL, PageBreak, Paragraph, Spacer, Table, TableStyle,
    callout, code, colors, inch, para, render, table,
)
from terminal_art import Annotated, TerminalWindow  # noqa: E402


def step(number, title):
    # Padding rather than a fixed row height: a fixed height clipped the digit,
    # because the cell does not account for the font's descent.
    badge = Table([[Paragraph(f"{number}", S("n", fontName="Helvetica-Bold",
                                             fontSize=12, leading=14,
                                             textColor=colors.white,
                                             alignment=1))]],
                  colWidths=[0.33 * inch])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    t = Table([[badge, Paragraph(title, S("t", fontName="Helvetica-Bold",
                                          fontSize=13, leading=17,
                                          textColor=INK))]],
              colWidths=[0.5 * inch, 5.8 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.8, RULE),
    ]))
    return t


def story():
    # ================= COVER =================
    yield Spacer(1, 0.8 * inch)
    yield para("ILLUSTRATED WALKTHROUGH", KICKER)
    yield para("Using the Terminal",
               S("cover", fontName="Helvetica-Bold", fontSize=27, leading=31,
                 textColor=INK, spaceAfter=10))
    yield para("Every command, shown as a picture, with what comes back.",
               S("sub", parent=LEAD, fontSize=13, leading=19, textColor=MUTED))

    yield Spacer(1, 0.35 * inch)
    yield callout(
        "First: you never open the client secret file",
        "If you have been looking for how to open it, that is why nothing has "
        "made sense. There is no such step.<br/><br/>"
        "The file Google gave you is read by the <b>software</b>, not by you. "
        "You move it into a folder, and that is the last time you think about "
        "it. You never open it, never read it, never copy anything out of it, "
        "and never send it to anyone — including me.<br/><br/>"
        "Nothing is missing. Move the file, and you are done with it.", "warn")

    yield Spacer(1, 0.3 * inch)
    yield para("What this document covers", H2)
    yield para(
        "Opening the Terminal, understanding what you are looking at, getting "
        "to the right folder, and the three commands that move that file. "
        "Nothing else.", BODY)
    yield para(
        "The pictures are drawings, not screenshots — but every line of text "
        "inside them is real, captured by running the commands. Your window "
        "may use different colours. The words will match.", SMALL)

    yield PageBreak()

    # ================= ANATOMY =================
    yield para("What you are looking at", H1)
    yield para(
        "Open the Terminal first: press <b>Command</b> and <b>Space</b> "
        "together, type <b>terminal</b>, press <b>Return</b>. A window like "
        "this appears.", LEAD)

    yield TerminalWindow([
        ("out", "Last login: Fri Aug 28 09:12:04 on ttys000"),
        ("blank", ""),
        ("type", ""),
    ])
    yield Annotated("You type here. The text before it is not yours — leave it alone.")

    yield Spacer(1, 12)
    yield para("The three parts of every line", H2)
    yield table(
        ["Part", "What it is"],
        [["<font face='Courier'>your-mac ~ %</font>",
          "The <b>prompt</b>. The computer printing \"ready\". It is already "
          "there — you never type it. Yours will show your own Mac's name, and "
          "may end in <font face='Courier'>%</font> or "
          "<font face='Courier'>$</font>. Either is fine."],
         ["What you type",
          "Goes after the prompt. Nothing happens until you press "
          "<b>Return</b>."],
         ["What comes back",
          "Printed underneath, starting at the left edge with no prompt in "
          "front of it."]],
        [1.5 * inch, 4.75 * inch])

    yield Spacer(1, 14)
    yield callout(
        "The most important thing in this document",
        "<b>Most commands print nothing when they work.</b> No message, no "
        "confirmation, just a fresh prompt on the next line.<br/><br/>"
        "That feels wrong — it looks like nothing happened. It is the opposite: "
        "silence is success. The terminal only speaks up when something went "
        "wrong. If you see a new prompt and no red text, it worked.")

    yield Spacer(1, 12)
    yield para("Two habits worth having", H3)
    yield table(
        None,
        [["Copy and paste",
          "You do not have to type these by hand. Copy from this document, "
          "click in the Terminal window, press <b>Command + V</b>, press "
          "<b>Return</b>. Fewer typos."],
         ["Press the up arrow",
          "Brings back the last command you ran, so you can fix one character "
          "instead of retyping the line."]],
        [1.5 * inch, 4.75 * inch])

    yield PageBreak()

    # ================= FINDING THE FOLDER =================
    yield para("Getting to the right folder", H1)
    yield para(
        "The Terminal is always \"in\" one folder at a time, and commands act "
        "on wherever it is. Most confusion comes from being in the wrong one.", LEAD)

    yield step(1, "Ask where you are")
    yield para("Type this and press Return:", BODY)
    yield TerminalWindow([
        ("type", "pwd"),
        ("out", "/Users/you"),
        ("blank", ""),
        ("type", ""),
    ])
    yield para(
        "<font face='Courier'>pwd</font> means \"print working directory\" — "
        "where am I. When you first open the Terminal you are in your home "
        "folder, shown as <font face='Courier'>/Users/you</font> (with your "
        "own name in place of <font face='Courier'>you</font>).", BODY)

    yield Spacer(1, 8)
    yield step(2, "Go to the project folder — the easy way")
    yield para(
        "Rather than typing a long path and mistyping it, let the Mac fill it "
        "in for you:", BODY)
    yield table(
        None,
        [["a.", "In the Terminal, type <font face='Courier'>cd</font> then a "
                "<b>space</b>. Do not press Return yet."],
         ["b.", "Open <b>Finder</b> and find your <b>milli</b> project folder."],
         ["c.", "<b>Drag that folder</b> from Finder onto the Terminal window "
                "and let go."],
         ["d.", "The full path appears by itself. Now press <b>Return</b>."]],
        [0.3 * inch, 5.95 * inch])

    yield Spacer(1, 10)
    yield para("It will look something like this:", BODY)
    yield TerminalWindow([
        ("type", "cd /Users/you/Documents/milli"),
        ("note", "the path after 'cd ' was filled in by dragging the folder"),
        ("blank", ""),
        ("type", "pwd"),
        ("out", "/Users/you/Documents/milli"),
        ("blank", ""),
        ("type", ""),
    ])
    yield para(
        "<font face='Courier'>cd</font> means \"change directory\" — go to "
        "this folder. Running <font face='Courier'>pwd</font> again confirms "
        "you arrived.", BODY)

    yield Spacer(1, 10)
    yield callout(
        "If it says \"No such file or directory\"",
        "The path was wrong — usually a typo, or the folder is somewhere other "
        "than you thought. Do not try variations. Use the drag trick above; it "
        "cannot produce a wrong path.")

    yield PageBreak()

    # ================= THE THREE COMMANDS =================
    yield para("Moving the credentials file", H1)
    yield para(
        "Three commands. The first two print nothing, and that is correct. "
        "The third is the one that shows you it worked.", LEAD)

    yield callout(
        "Before you start",
        "The file should be in your Downloads folder, with a long name "
        "beginning <font face='Courier'>client_secret</font>. If you are not "
        "sure it downloaded, step 0 below checks.")

    yield Spacer(1, 12)
    yield step(0, "Check the file is actually there")
    yield TerminalWindow([
        ("type", "ls ~/Downloads"),
        ("out", "client_secret_847263910284-a7f3k9d2m1p0q8s6.apps.google"),
        ("out", "usercontent.com.json"),
        ("blank", ""),
        ("type", ""),
    ])
    yield para(
        "<font face='Courier'>ls</font> means \"list\" — show me what is in "
        "this folder. The <font face='Courier'>~</font> is shorthand for your "
        "home folder, so <font face='Courier'>~/Downloads</font> is your "
        "Downloads folder wherever you happen to be standing.", BODY)
    yield para(
        "You will see everything else in Downloads too. You are only looking "
        "for the one starting <font face='Courier'>client_secret</font>. It is "
        "long and it wraps onto two lines — that is one filename, not two.", BODY)

    yield Spacer(1, 12)
    yield step(1, "Make the folder it will live in")
    yield TerminalWindow([
        ("type", "mkdir -p ~/er-sync"),
        ("blank", ""),
        ("type", ""),
        ("note", "nothing printed. that means it worked."),
    ])
    yield para(
        "<font face='Courier'>mkdir</font> means \"make directory\". The "
        "<font face='Courier'>-p</font> tells it not to complain if the folder "
        "already exists, so this is safe to run twice.", BODY)

    yield PageBreak()

    yield step(2, "Move and rename the file, in one go")
    yield TerminalWindow([
        ("type", "mv ~/Downloads/client_secret*.json ~/er-sync/credentials.json"),
        ("blank", ""),
        ("type", ""),
        ("note", "nothing printed again. still correct."),
    ])
    yield para(
        "<font face='Courier'>mv</font> means \"move\". It takes the file from "
        "the first place and puts it in the second — and because the second "
        "ends in a new name, it renames it at the same time.", BODY)

    yield Spacer(1, 6)
    yield para("Why the star", H3)
    yield para(
        "<font face='Courier'>client_secret*.json</font> means \"anything that "
        "starts with <font face='Courier'>client_secret</font> and ends with "
        "<font face='Courier'>.json</font>\". The "
        "<font face='Courier'>*</font> saves you typing that long jumble of "
        "numbers exactly. You never type the real name.", BODY)

    yield Spacer(1, 12)
    yield step(3, "Confirm it arrived")
    yield TerminalWindow([
        ("type", "ls ~/er-sync"),
        ("out", "credentials.json"),
        ("blank", ""),
        ("type", ""),
    ])
    yield para(
        "<b>This is the whole test.</b> If it prints "
        "<font face='Courier'>credentials.json</font>, you are finished with "
        "this file forever. Do not open it. Do not look inside it. The software "
        "reads it from here when it needs to.", BODY)

    yield Spacer(1, 14)
    yield callout(
        "What if I already opened it, out of curiosity?",
        "No harm done — opening a file does not change it. Close it without "
        "saving and carry on. The only thing that matters is that you do not "
        "send its contents to anyone, and that it stays in "
        "<font face='Courier'>~/er-sync</font>.")

    yield PageBreak()

    # ================= WHEN IT GOES WRONG =================
    yield para("When a command complains", H1)
    yield para(
        "Three messages you might see, what each means, and what to do. Every "
        "one of these is recoverable.", LEAD)

    yield para("\"No such file or directory\"", H2)
    yield TerminalWindow([
        ("type", "mv ~/Downloads/client_secret*.json ~/er-sync/credentials.json"),
        ("out", "mv: rename /Users/you/Downloads/client_secret*.json to"),
        ("out", "/Users/you/er-sync/credentials.json: No such file or directory"),
        ("blank", ""),
        ("type", ""),
    ])
    yield para(
        "Nothing starting with <font face='Courier'>client_secret</font> is in "
        "Downloads. Either the download did not happen, or Chrome saved it "
        "somewhere else.", BODY)
    yield para(
        "<b>What to do:</b> run <font face='Courier'>ls ~/Downloads</font> and "
        "look. If the file is not there, download it again from the Google "
        "Cloud Console — Credentials, find your client, press the download "
        "icon on its row. You can download it as many times as you like.", BODY)

    yield Spacer(1, 14)
    yield para("\"Not a directory\"", H2)
    yield TerminalWindow([
        ("type", "mv ~/Downloads/client_secret*.json ~/er-sync/credentials.json"),
        ("out", "mv: target /Users/you/er-sync/credentials.json:"),
        ("out", "Not a directory"),
        ("blank", ""),
        ("type", ""),
    ])
    yield para(
        "This one sounds like nonsense and has a simple cause: <b>you "
        "downloaded the file more than once</b>. The "
        "<font face='Courier'>*</font> now matches several files, and several "
        "files cannot all become one file.", BODY)
    yield para(
        "<b>What to do:</b> open your Downloads folder in Finder, delete every "
        "<font face='Courier'>client_secret</font> file except the newest, "
        "then run the command again.", BODY)

    yield PageBreak()

    yield para("\"command not found\"", H2)
    yield TerminalWindow([
        ("type", "ls ~/er-sync"),
        ("out", "zsh: command not found: ls"),
        ("blank", ""),
        ("type", ""),
    ])
    yield para(
        "Almost always a typo, or a stray character pasted in with the "
        "command. Check the spelling and that there is nothing extra at the "
        "start of the line.", BODY)

    yield Spacer(1, 16)
    yield para("The safe reset", H2)
    yield para(
        "If you are lost, none of these commands has broken anything. "
        "<font face='Courier'>ls</font> and <font face='Courier'>pwd</font> "
        "only look; <font face='Courier'>mkdir</font> only adds a folder. "
        "Close the Terminal window, open a new one, and start again from "
        "<font face='Courier'>pwd</font>.", BODY)
    yield para(
        "The one command that changes anything is "
        "<font face='Courier'>mv</font>, and the worst it can do is put the "
        "file somewhere unexpected. Nothing is lost.", BODY)

    yield Spacer(1, 18)
    yield para("The whole sequence, together", H2)
    yield para("For when you just want the four lines:", SMALL)
    yield TerminalWindow([
        ("type", "ls ~/Downloads"),
        ("out", "client_secret_847263910284-a7f3k9d2m1p0q8s6.apps.google"),
        ("out", "usercontent.com.json"),
        ("blank", ""),
        ("type", "mkdir -p ~/er-sync"),
        ("type", "mv ~/Downloads/client_secret*.json ~/er-sync/credentials.json"),
        ("type", "ls ~/er-sync"),
        ("out", "credentials.json"),
        ("blank", ""),
        ("type", ""),
        ("note", "done. you never touch that file again."),
    ])

    yield Spacer(1, 16)
    yield callout(
        "Still stuck?",
        "Take a photo or a screenshot of the Terminal window, exactly as it "
        "is, and send it to me. The text of the error is enough for me to tell "
        "you the next command. There is nothing sensitive in an error message "
        "— but if the window happens to show anything from ExtendedReach, "
        "leave that part out.")


def build():
    render(OUT, story(),
           running_head="ExtendedReach Report Sync  |  Terminal Walkthrough",
           title="Using the Terminal - Illustrated Walkthrough",
           subject="Step-by-step terminal instructions for the credentials file")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
