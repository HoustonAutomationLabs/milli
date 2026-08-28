const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.3 x 7.5
pres.author = "Houston Strong CPA";
pres.title  = "ExtendedReach Report Automation";

const INK   = "2A2622";   // deep warm charcoal
const CLAY  = "B85042";   // terracotta
const SAGE  = "6E8B7B";   // muted sage
const SAND  = "F0EBE3";
const WHITE = "FFFFFF";
const MUTE  = "6B635B";
const W = 13.3, H = 7.5, M = 0.7;

const HEAD = "Century Schoolbook";
const BODY = "Calibri";

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: INK };
  return s;
}
function lightSlide() {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  return s;
}
function title(s, text, opts = {}) {
  s.addText(text, {
    x: M, y: opts.y || 0.55, w: W - M * 2, h: 0.9,
    fontFace: HEAD, fontSize: opts.size || 34, bold: true,
    color: opts.color || INK, isTextBox: true, margin: 0,
  });
}
function kicker(s, text, color) {
  s.addText(text.toUpperCase(), {
    x: M, y: 0.3, w: W - M * 2, h: 0.28,
    fontFace: BODY, fontSize: 11, bold: true, charSpacing: 1.6,
    color: color || CLAY, isTextBox: true, margin: 0,
  });
}
// A content card. No edge stripes — a tint and a shadow only.
function card(s, x, y, w, h, fill) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06,
    fill: { color: fill || SAND }, line: { color: fill || SAND },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 1, angle: 90, opacity: 0.07 },
  });
}
function bullets(s, items, x, y, w, opts = {}) {
  s.addText(items.map((t, i) => ({
    text: t, options: { bullet: true, breakLine: i !== items.length - 1 },
  })), {
    x, y, w, h: opts.h || 2.6, fontFace: BODY, fontSize: opts.size || 15,
    color: opts.color || INK, lineSpacing: 22, paraSpaceAfter: 9,
    isTextBox: true, margin: 0,
  });
}

/* ---------------------------------------------------------- 1. TITLE */
{
  const s = darkSlide();
  s.addText("PROPOSAL FOR DECISION", {
    x: M, y: 2.25, w: 9, h: 0.3, fontFace: BODY, fontSize: 12, bold: true,
    charSpacing: 2, color: CLAY, isTextBox: true, margin: 0,
  });
  s.addText("Automating the daily\nExtendedReach exports", {
    x: M, y: 2.7, w: 10, h: 1.9, fontFace: HEAD, fontSize: 42, bold: true,
    color: WHITE, lineSpacing: 46, isTextBox: true, margin: 0,
  });
  s.addText("Nine reports, pulled and filed every day, without anyone doing it by hand.", {
    x: M, y: 4.75, w: 9.5, h: 0.5, fontFace: BODY, fontSize: 16,
    color: "C9C2B8", isTextBox: true, margin: 0,
  });
  s.addText("Houston Strong CPA  |  Foster Care", {
    x: M, y: 6.5, w: 8, h: 0.3, fontFace: BODY, fontSize: 11,
    color: MUTE, isTextBox: true, margin: 0,
  });
  s.addNotes("One sentence to open: we already pull these reports by hand every day. This is a proposal to have that happen on a timer instead. I am asking for a decision on two things, both on the last slide.");
}

/* ---------------------------------------------------------- 2. TODAY */
{
  const s = lightSlide();
  kicker(s, "The situation today");
  title(s, "Nine reports. By hand. Every day.");

  const steps = [
    ["1", "Sign in", "Including the two-factor code"],
    ["2", "Open a report", "Menu, submenu, apply filters"],
    ["3", "Click Excel", "Wait for the download"],
    ["4", "Repeat  x9", "Then file them somewhere"],
  ];
  steps.forEach(([n, h, d], i) => {
    const x = M + i * 3.05;
    card(s, x, 1.95, 2.8, 1.85);
    s.addShape(pres.ShapeType.ellipse, {
      x: x + 0.25, y: 2.2, w: 0.42, h: 0.42,
      fill: { color: CLAY }, line: { color: CLAY },
    });
    s.addText(n, { x: x + 0.25, y: 2.24, w: 0.42, h: 0.34, align: "center",
      fontFace: BODY, fontSize: 14, bold: true, color: WHITE, isTextBox: true, margin: 0 });
    s.addText(h, { x: x + 0.25, y: 2.78, w: 2.3, h: 0.3, fontFace: BODY,
      fontSize: 15, bold: true, color: INK, isTextBox: true, margin: 0 });
    s.addText(d, { x: x + 0.25, y: 3.1, w: 2.35, h: 0.6, fontFace: BODY,
      fontSize: 11.5, color: MUTE, isTextBox: true, margin: 0 });
  });

  s.addText([
    { text: "Roughly 15–20 minutes a day", options: { bold: true } },
    { text: "  — call it an hour and a half a week. But the cost is not really the minutes." },
  ], { x: M, y: 4.35, w: W - M * 2, h: 0.4, fontFace: BODY, fontSize: 16,
       color: INK, isTextBox: true, margin: 0 });

  card(s, M, 5.0, W - M * 2, 1.4, SAND);
  s.addText("It is that when the day gets busy, this is the task that gets skipped. Then the numbers leadership is looking at are three days old, and nobody knows which three days.",
    { x: M + 0.35, y: 5.25, w: W - M * 2 - 0.7, h: 0.95, fontFace: BODY,
      fontSize: 15, italic: true, color: INK, isTextBox: true, margin: 0 });
  s.addNotes("The time saving is real but modest. Lead with the reliability argument instead: manual daily tasks get skipped under pressure, and stale data is worse than no data because nobody knows it is stale.");
}

/* ---------------------------------------------------------- 3. WHY IT MATTERS */
{
  const s = lightSlide();
  kicker(s, "Why current data matters");
  title(s, "What these reports are tracking");

  const stats = [
    ["1,556", "obligations overdue", "902 are actionable today"],
    ["394", "submissions awaiting approval", "one approver holds 202 of them"],
    ["41%", "of work completed on time", "across 3,184 completed items"],
  ];
  stats.forEach(([big, label, sub], i) => {
    const x = M + i * 4.05;
    s.addText(big, { x, y: 2.0, w: 3.7, h: 1.15, fontFace: HEAD, fontSize: 60,
      bold: true, color: CLAY, isTextBox: true, margin: 0 });
    s.addText(label, { x, y: 3.15, w: 3.7, h: 0.35, fontFace: BODY, fontSize: 15,
      bold: true, color: INK, isTextBox: true, margin: 0 });
    s.addText(sub, { x, y: 3.5, w: 3.7, h: 0.5, fontFace: BODY, fontSize: 12.5,
      color: MUTE, isTextBox: true, margin: 0 });
  });

  card(s, M, 4.5, W - M * 2, 1.75, SAND);
  s.addText("These are our real figures, from the audit.", {
    x: M + 0.35, y: 4.75, w: 11, h: 0.3, fontFace: BODY, fontSize: 14,
    bold: true, color: INK, isTextBox: true, margin: 0 });
  s.addText("They move every day. A backlog number from last Tuesday tells you very little about who needs help today — and the approval queue, which is the harder bottleneck, moves fastest of all.",
    { x: M + 0.35, y: 5.1, w: 11.6, h: 0.9, fontFace: BODY, fontSize: 14,
      color: MUTE, isTextBox: true, margin: 0 });
  s.addNotes("These numbers are from our own de-identified export, not estimates. The point of the slide is that the figures move daily, so a weekly manual pull is not good enough to act on.");
}

/* ---------------------------------------------------------- 4. WHAT IT DOES */
{
  const s = lightSlide();
  kicker(s, "The proposal");
  title(s, "The same clicks, on a timer");

  card(s, M, 1.9, 6.0, 4.4);
  s.addText("What it does, once a day", { x: M + 0.4, y: 2.15, w: 5.2, h: 0.35,
    fontFace: BODY, fontSize: 16, bold: true, color: INK, isTextBox: true, margin: 0 });
  bullets(s, [
    "Opens a browser that is already signed in",
    "Goes to each of the nine reports in turn",
    "Clicks the same export button a person clicks",
    "Checks each file is genuinely the report",
    "Files it in Google Drive, named and dated",
    "Writes down what happened, for review",
  ], M + 0.4, 2.6, 5.2, { size: 14.5, h: 3.4 });

  card(s, 7.1, 1.9, W - 7.1 - M, 4.4, INK);
  s.addText("What it is not", { x: 7.5, y: 2.15, w: 5.0, h: 0.35,
    fontFace: BODY, fontSize: 16, bold: true, color: SAGE, isTextBox: true, margin: 0 });
  s.addText("It is not an AI reading our case files and deciding things.", {
    x: 7.5, y: 2.6, w: 4.9, h: 0.9, fontFace: BODY, fontSize: 15,
    color: WHITE, isTextBox: true, margin: 0 });
  s.addText("It presses fixed buttons in a fixed order. It cannot create, edit, approve, reject, submit or delete anything in ExtendedReach — that is built into how it works, not a policy we are trusting it to follow.",
    { x: 7.5, y: 3.5, w: 4.9, h: 1.8, fontFace: BODY, fontSize: 14,
      color: "C9C2B8", isTextBox: true, margin: 0 });
  s.addText("Read-only. By construction.", {
    x: 7.5, y: 5.5, w: 4.9, h: 0.4, fontFace: BODY, fontSize: 15,
    bold: true, italic: true, color: SAGE, isTextBox: true, margin: 0 });
  s.addNotes("If anyone asks the AI question, this slide is the answer. Nothing decides anything. It clicks the same buttons in the same order every time, and it physically cannot press the buttons that change records.");
}

/* ---------------------------------------------------------- 5. SAFEGUARDS */
{
  const s = lightSlide();
  kicker(s, "Protecting the data");
  title(s, "These are children's records");

  const rows = [
    ["Nobody's password is stored", "A person signs in once, by hand. There is no place in the system to put a password, and no code that types one."],
    ["It cannot change anything", "Only a fixed list of read-only actions is possible. It refuses to even visit a page whose address contains words like delete or approve."],
    ["Nothing is filed unchecked", "Every file is opened and verified before it is uploaded. A failed export is never passed off as a real report."],
    ["No case details in the logs", "The record of what happened is scrubbed automatically. It says which report and whether it worked, never who is in it."],
  ];
  rows.forEach(([h, d], i) => {
    const y = 1.9 + i * 1.15;
    s.addShape(pres.ShapeType.ellipse, { x: M, y: y + 0.06, w: 0.34, h: 0.34,
      fill: { color: SAGE }, line: { color: SAGE } });
    s.addText(h, { x: M + 0.55, y: y, w: 4.6, h: 0.4, fontFace: BODY,
      fontSize: 15, bold: true, color: INK, isTextBox: true, margin: 0 });
    s.addText(d, { x: 5.5, y: y - 0.02, w: W - 5.5 - M, h: 1.0, fontFace: BODY,
      fontSize: 13.5, color: MUTE, isTextBox: true, margin: 0 });
  });
  s.addNotes("This is the slide to slow down on. The safeguards are structural, not promises. If someone asks what happens if it goes wrong: it stops and files nothing. It never uploads something it could not verify.");
}

/* ---------------------------------------------------------- 6. STATUS */
{
  const s = lightSlide();
  kicker(s, "Where it stands");
  title(s, "Built and tested. Not yet connected.");

  card(s, M, 1.95, 5.9, 2.05, SAND);
  s.addText("Done", { x: M + 0.4, y: 2.2, w: 5.0, h: 0.32, fontFace: BODY,
    fontSize: 15, bold: true, color: SAGE, isTextBox: true, margin: 0 });
  bullets(s, [
    "The software is written and reviewed",
    "129 automated checks pass",
    "Handles all nine reports",
  ], M + 0.4, 2.6, 5.0, { size: 13.5, h: 1.3 });

  card(s, 7.0, 1.95, W - 7.0 - M, 2.05, SAND);
  s.addText("Not done", { x: 7.4, y: 2.2, w: 5.0, h: 0.32, fontFace: BODY,
    fontSize: 15, bold: true, color: CLAY, isTextBox: true, margin: 0 });
  bullets(s, [
    "It has never touched our portal",
    "Needs one sitting to point it at our reports",
    "Then a supervised first run",
  ], 7.4, 2.6, 5.0, { size: 13.5, h: 1.3 });

  card(s, M, 4.3, W - M * 2, 1.9, INK);
  s.addText("I want to be straight about this", {
    x: M + 0.4, y: 4.55, w: 11.5, h: 0.32, fontFace: BODY, fontSize: 15,
    bold: true, color: SAGE, isTextBox: true, margin: 0 });
  s.addText("The tested part is the software's own logic — the checking, the naming, the safety rules. It has not yet been run against ExtendedReach, because that needs an authorised account and about an hour of setup. Until that happens I cannot promise it works end to end, and I am not going to.",
    { x: M + 0.4, y: 4.95, w: 11.5, h: 1.1, fontFace: BODY, fontSize: 14,
      color: "C9C2B8", isTextBox: true, margin: 0 });
  s.addNotes("Do not oversell this. Saying it is tested but not yet connected is what makes the rest of the deck credible. If asked how long to prove it: one working session plus a week of supervised runs.");
}

/* ---------------------------------------------------------- 7. WHAT IT COSTS */
{
  const s = lightSlide();
  kicker(s, "What it takes");
  title(s, "Cost and effort");

  const cols = [
    ["Money", "$0", "No new subscription. It uses the ExtendedReach account and Google Drive we already pay for."],
    ["Setup", "~1 hour", "One sitting to point it at our nine reports, then a supervised first run."],
    ["Upkeep", "2 min", "A weekly glance at a status screen that says plainly whether anything needs attention."],
  ];
  cols.forEach(([h, big, d], i) => {
    const x = M + i * 4.05;
    card(s, x, 1.95, 3.75, 3.3);
    s.addText(h.toUpperCase(), { x: x + 0.35, y: 2.2, w: 3.0, h: 0.28,
      fontFace: BODY, fontSize: 11, bold: true, charSpacing: 1.4,
      color: MUTE, isTextBox: true, margin: 0 });
    s.addText(big, { x: x + 0.35, y: 2.55, w: 3.1, h: 0.85, fontFace: HEAD,
      fontSize: 38, bold: true, color: CLAY, isTextBox: true, margin: 0 });
    s.addText(d, { x: x + 0.35, y: 3.5, w: 3.05, h: 1.5, fontFace: BODY,
      fontSize: 13, color: INK, isTextBox: true, margin: 0 });
  });

  s.addText("The one ongoing human task: when the ExtendedReach session expires, somebody signs in again. The system will not do that itself, on purpose.",
    { x: M, y: 5.6, w: W - M * 2, h: 0.7, fontFace: BODY, fontSize: 14.5,
      italic: true, color: MUTE, isTextBox: true, margin: 0 });
  s.addNotes("If pressed on why sign-in is not automated: automating a login and its two-factor code would mean storing credentials, which is exactly what we should not do with a system holding children's records.");
}

/* ---------------------------------------------------------- 8. DECISIONS */
{
  const s = lightSlide();
  kicker(s, "What I need from you");
  title(s, "Two decisions");

  card(s, M, 1.95, 5.9, 3.6);
  s.addShape(pres.ShapeType.ellipse, { x: M + 0.4, y: 2.25, w: 0.5, h: 0.5,
    fill: { color: CLAY }, line: { color: CLAY } });
  s.addText("1", { x: M + 0.4, y: 2.3, w: 0.5, h: 0.4, align: "center",
    fontFace: BODY, fontSize: 17, bold: true, color: WHITE, isTextBox: true, margin: 0 });
  s.addText("Where do the files land?", { x: M + 0.4, y: 2.95, w: 5.1, h: 0.4,
    fontFace: BODY, fontSize: 17, bold: true, color: INK, isTextBox: true, margin: 0 });
  s.addText("These reports carry names, dates of birth and Medicaid numbers. They should go to a Google Workspace account the agency controls and has a signed agreement for — not a personal Google account. I need confirmation of which account, and who may see the folder.",
    { x: M + 0.4, y: 3.45, w: 5.1, h: 1.9, fontFace: BODY, fontSize: 13.5,
      color: MUTE, isTextBox: true, margin: 0 });

  card(s, 7.0, 1.95, W - 7.0 - M, 3.6);
  s.addShape(pres.ShapeType.ellipse, { x: 7.4, y: 2.25, w: 0.5, h: 0.5,
    fill: { color: CLAY }, line: { color: CLAY } });
  s.addText("2", { x: 7.4, y: 2.3, w: 0.5, h: 0.4, align: "center",
    fontFace: BODY, fontSize: 17, bold: true, color: WHITE, isTextBox: true, margin: 0 });
  s.addText("May I connect it to our account?", { x: 7.4, y: 2.95, w: 5.1, h: 0.4,
    fontFace: BODY, fontSize: 17, bold: true, color: INK, isTextBox: true, margin: 0 });
  s.addText("Approval to point it at our real ExtendedReach account and run it, supervised, for one week before it runs on its own. Nothing is uploaded during that week without someone looking at it first.",
    { x: 7.4, y: 3.45, w: 5.1, h: 1.9, fontFace: BODY, fontSize: 13.5,
      color: MUTE, isTextBox: true, margin: 0 });

  s.addText("Worth checking separately: whether our agreement with ExtendedReach has anything to say about automated access. One email to them settles it.",
    { x: M, y: 5.85, w: W - M * 2, h: 0.6, fontFace: BODY, fontSize: 13.5,
      italic: true, color: MUTE, isTextBox: true, margin: 0 });
  s.addNotes("Do not skip the ExtendedReach terms point. Better to raise it ourselves than have it surface later. It is one email and it protects us.");
}

/* ---------------------------------------------------------- 9. CLOSE */
{
  const s = darkSlide();
  s.addText("IF APPROVED", { x: M, y: 1.5, w: 8, h: 0.3, fontFace: BODY,
    fontSize: 12, bold: true, charSpacing: 2, color: CLAY, isTextBox: true, margin: 0 });
  s.addText("What happens next", { x: M, y: 1.95, w: 10, h: 0.8,
    fontFace: HEAD, fontSize: 36, bold: true, color: WHITE, isTextBox: true, margin: 0 });

  const plan = [
    ["This week", "One hour of setup, pointing it at our nine reports"],
    ["Next week", "Supervised runs. Every file checked by hand before it is trusted"],
    ["After that", "It runs on a timer. Two minutes a week to confirm it is healthy"],
  ];
  plan.forEach(([when, what], i) => {
    const y = 3.15 + i * 1.05;
    s.addText(when, { x: M, y, w: 2.2, h: 0.35, fontFace: BODY, fontSize: 15,
      bold: true, color: SAGE, isTextBox: true, margin: 0 });
    s.addText(what, { x: M + 2.4, y, w: 9.2, h: 0.6, fontFace: BODY,
      fontSize: 15, color: "C9C2B8", isTextBox: true, margin: 0 });
  });

  s.addText("If it does not work against our portal, we will know within a week — and we will have spent an hour finding out.",
    { x: M, y: 6.35, w: 11.5, h: 0.5, fontFace: BODY, fontSize: 14,
      italic: true, color: MUTE, isTextBox: true, margin: 0 });
  s.addNotes("Close on the low downside: the cost of being wrong is one hour. That is usually the sentence that gets a yes.");
}

pres.writeFile({ fileName: "ExtendedReach-Automation-Proposal.pptx" })
  .then(f => console.log("wrote", f));
