"""Drawn pictures of a macOS Terminal window, for the walkthrough document.

These are illustrations, not screenshots. That is deliberate: a faked
screenshot of someone else's software invites the reader to match it
pixel-for-pixel and doubt themselves when their version differs. A drawing
that is obviously a drawing carries the same information — what to type, what
comes back — without pretending to be the real window.

The text inside every window is real output, captured by running the commands.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Flowable

# A dark terminal, close enough to the macOS default to be recognisable.
BG = colors.HexColor("#1f1d1b")
BAR = colors.HexColor("#3a3735")
BAR_TEXT = colors.HexColor("#cfcac4")
PROMPT = colors.HexColor("#8fb98a")      # the part you do not type
TYPED = colors.HexColor("#ffffff")       # the part you type
OUTPUT = colors.HexColor("#bdb8b2")      # what comes back
DIM = colors.HexColor("#8a847d")
NOTE = colors.HexColor("#e0a45e")        # annotation ink

LINE_HEIGHT = 13.5
FONT = "Courier"
FONT_BOLD = "Courier-Bold"
SIZE = 8.6
BAR_HEIGHT = 17
PAD_X = 11
PAD_TOP = 9
PAD_BOTTOM = 11


class TerminalWindow(Flowable):
    """One drawn terminal window.

    `lines` is a list of (kind, text) pairs:
        "type"    a line you type, shown after a prompt
        "out"     a line the computer prints back
        "blank"   spacing
        "note"    an annotation in the margin ink, not part of the session
    """

    def __init__(self, lines, width=6.3 * inch, title="Terminal",
                 caption=None):
        super().__init__()
        self.lines = lines
        self.width = width
        self.title = title
        self.caption = caption
        body = len(lines) * LINE_HEIGHT
        self.height = BAR_HEIGHT + PAD_TOP + body + PAD_BOTTOM

    def wrap(self, available_width, available_height):
        return self.width, self.height

    def draw(self):
        c = self.canv
        h = self.height

        # Window body and title bar.
        c.setFillColor(BG)
        c.roundRect(0, 0, self.width, h, 5, stroke=0, fill=1)
        c.setFillColor(BAR)
        c.roundRect(0, h - BAR_HEIGHT, self.width, BAR_HEIGHT, 5, stroke=0, fill=1)
        c.rect(0, h - BAR_HEIGHT, self.width, 5, stroke=0, fill=1)

        # The three window buttons.
        for index, shade in enumerate(("#ff5f57", "#febc2e", "#28c840")):
            c.setFillColor(colors.HexColor(shade))
            c.circle(13 + index * 13, h - BAR_HEIGHT / 2, 3.6, stroke=0, fill=1)

        c.setFillColor(BAR_TEXT)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(self.width / 2, h - BAR_HEIGHT / 2 - 2.6, self.title)

        # Session text.
        y = h - BAR_HEIGHT - PAD_TOP - SIZE
        for kind, text in self.lines:
            if kind == "blank":
                y -= LINE_HEIGHT
                continue
            if kind == "note":
                c.setFillColor(NOTE)
                c.setFont("Helvetica-Oblique", 7.8)
                c.drawString(PAD_X, y, text)
                y -= LINE_HEIGHT
                continue
            if kind == "type":
                c.setFillColor(PROMPT)
                c.setFont(FONT, SIZE)
                prefix = "your-mac ~ % "
                c.drawString(PAD_X, y, prefix)
                c.setFillColor(TYPED)
                c.setFont(FONT_BOLD, SIZE)
                c.drawString(PAD_X + c.stringWidth(prefix, FONT, SIZE), y, text)
            else:
                c.setFillColor(OUTPUT)
                c.setFont(FONT, SIZE)
                c.drawString(PAD_X, y, text)
            y -= LINE_HEIGHT


class Annotated(Flowable):
    """A label to the right of a boxed area, joined by a drawn line.

    The line and its arrow head are drawn as vector shapes rather than typed
    characters: ReportLab's built-in fonts have no arrow glyph, and a missing
    glyph renders as a solid black box.
    """

    def __init__(self, text, width=6.3 * inch, height=26, from_top=True):
        super().__init__()
        self.text = text
        self.width = width
        self.height = height
        self.from_top = from_top

    def wrap(self, available_width, available_height):
        return self.width, self.height

    def draw(self):
        c = self.canv
        y = self.height - 8
        c.setStrokeColor(NOTE)
        c.setLineWidth(1)
        c.setDash(2, 2)
        c.line(38, self.height, 38, 9)
        c.line(38, 9, 54, 9)
        c.setDash()
        # Arrow head.
        c.setFillColor(NOTE)
        p = c.beginPath()
        p.moveTo(54, 9)
        p.lineTo(48, 12)
        p.lineTo(48, 6)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        c.setFont("Helvetica-Bold", 8.2)
        c.drawString(60, 6, self.text)
