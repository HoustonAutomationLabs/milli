"""Interactive setup helper: capture the report URL and candidate selectors.

Filling in `workflow.json` by hand means opening Chrome DevTools and copying
CSS selectors. This does that part for you.

It is strictly read-only and makes no decisions. You sign in, you navigate to
the report you want, and this reads the page's DOM to list the elements that
*look* like a sign-in indicator or an export control. It never clicks
anything, never triggers a download, and never picks for you — it prints
numbered candidates and you choose.

The matching is plain regular expressions over element text and attributes.
Nothing here infers intent; if the portal calls its export button something
unexpected, the scan will miss it and you fall back to DevTools.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

# Builds a stable CSS selector for one element. Prefers an id, then a
# distinctive class, then falls back to a structural nth-of-type path.
# Runs in the page, so it must be plain JS with no dependencies.
_SELECTOR_JS = """
(el) => {
  const cssEscape = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : s;
  if (el.id && !/^\\d/.test(el.id) && document.querySelectorAll('#' + cssEscape(el.id)).length === 1) {
    return '#' + cssEscape(el.id);
  }
  // A single distinctive class is more readable, and survives layout changes
  // better than a positional path.
  for (const cls of Array.from(el.classList)) {
    const sel = el.tagName.toLowerCase() + '.' + cssEscape(cls);
    if (document.querySelectorAll(sel).length === 1) return sel;
  }
  for (const attr of ['name', 'data-testid', 'data-id', 'aria-label', 'title']) {
    const val = el.getAttribute(attr);
    if (val) {
      const sel = el.tagName.toLowerCase() + '[' + attr + '="' + val.replace(/"/g, '\\\\"') + '"]';
      try { if (document.querySelectorAll(sel).length === 1) return sel; } catch (e) {}
    }
  }
  // Structural fallback.
  const parts = [];
  let node = el;
  while (node && node.nodeType === 1 && parts.length < 6) {
    let part = node.tagName.toLowerCase();
    const parent = node.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter(c => c.tagName === node.tagName);
      if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
    }
    parts.unshift(part);
    if (node.id) { parts[0] = '#' + cssEscape(node.id); break; }
    node = node.parentElement;
  }
  return parts.join(' > ');
}
"""

# Element text is read only to match these patterns and to show you what you
# are choosing. It is never logged.
EXPORT_TEXT = re.compile(r"\b(excel|export|csv|download|spreadsheet|xlsx?)\b", re.I)
SIGNED_IN_TEXT = re.compile(r"\b(sign\s*out|log\s*out|logout|signout|my\s*account|profile)\b", re.I)
MFA_HINT = re.compile(r"\b(code|verification|authenticat|token|one[-\s]?time|otp)\b", re.I)

MAX_CANDIDATES = 12


def _describe(page, handle) -> Optional[dict[str, Any]]:
    """Selector plus a short label for one element."""
    try:
        selector = handle.evaluate(_SELECTOR_JS)
        text = (handle.inner_text() or "").strip().replace("\n", " ")
        tag = handle.evaluate("(el) => el.tagName.toLowerCase()")
        return {"selector": selector, "text": text[:60], "tag": tag}
    except Exception:
        return None


def _scan(page, pattern: re.Pattern[str], roles=("a", "button", "input")) -> list[dict[str, Any]]:
    """Every element whose visible text or accessible attributes match."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    for tag in roles:
        for handle in page.locator(tag).all():
            try:
                if not handle.is_visible():
                    continue
                haystack = " ".join(filter(None, [
                    handle.inner_text() or "",
                    handle.get_attribute("value") or "",
                    handle.get_attribute("aria-label") or "",
                    handle.get_attribute("title") or "",
                    handle.get_attribute("href") or "",
                ]))
            except Exception:
                continue
            if not pattern.search(haystack):
                continue
            described = _describe(page, handle)
            if described and described["selector"] not in seen:
                seen.add(described["selector"])
                found.append(described)
            if len(found) >= MAX_CANDIDATES:
                return found
    return found


def _choose(candidates: list[dict[str, Any]], what: str) -> Optional[str]:
    """Print numbered candidates and let the operator pick one."""
    if not candidates:
        print(f"\n  No obvious candidate found for the {what}.")
        print("  You will need to find this one in Chrome: right-click the")
        print("  element, Inspect, then right-click the highlighted markup ->")
        print("  Copy -> Copy selector.")
        return None

    print(f"\n  Candidates for the {what}:\n")
    for index, item in enumerate(candidates, start=1):
        label = item["text"] or f"<{item['tag']}>"
        print(f"    {index:2}. {label!r}")
        print(f"        {item['selector']}")

    while True:
        answer = input(f"\n  Which number is the {what}? "
                       "(Enter to skip) ").strip()
        if not answer:
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            return candidates[int(answer) - 1]["selector"]
        print("  Not one of the numbers listed.")


def run_setup_assist(cfg, log, out_path: Path) -> int:
    """Walk the operator through capturing what workflow.json needs.

    Returns 0 on success. Writes a draft workflow file; it never overwrites an
    existing one in place.
    """
    from src.browser_worker import BrowserWorker

    print("\n" + "=" * 70)
    print("  Setup assistant")
    print()
    print("  This opens a browser and watches. It clicks nothing, downloads")
    print("  nothing, and changes nothing in the portal. You drive.")
    print("=" * 70)

    with BrowserWorker(cfg, log, headed=True) as worker:
        page = worker.page
        worker.goto(cfg.base_url)

        # -- step 1: sign in --------------------------------------------
        print("\n  STEP 1 of 3 — Sign in")
        print("  Sign in in the browser window, including MFA if asked.")
        print("  Nothing here types anything for you.")
        input("\n  Press Enter once you can see the ExtendedReach home page. ")

        signed_in = _scan(page, SIGNED_IN_TEXT)
        auth_selector = _choose(
            signed_in, "element that only appears when you are signed in "
                       "(a Sign Out link is the usual one)")

        # -- step 2: the report -----------------------------------------
        print("\n  STEP 2 of 3 — Open the report")
        print("  Navigate to the ONE report you want exported automatically.")
        print("  Apply any filters you want it to use every time.")
        input("\n  Press Enter once the report is on screen. ")

        report_url = page.url
        print(f"\n  Captured report URL:\n    {report_url}")

        # -- step 3: the export control ---------------------------------
        print("\n  STEP 3 of 3 — Identify the export control")
        print("  Do NOT click it. Just identify it below.")
        export_candidates = _scan(page, EXPORT_TEXT)
        export_selector = _choose(export_candidates, "export/Excel control")

        # A best-effort look for a challenge field. Usually absent while
        # signed in, which is why it stays a TODO rather than a guess.
        mfa_candidates = _scan(page, MFA_HINT, roles=("input",))

    # -- write the draft --------------------------------------------------
    example = json.loads(
        (out_path.parent / "workflow.example.json").read_text(encoding="utf-8"))

    # The example's "$comment" blocks explain how to fill each field in. Once
    # the fields are filled they are just noise, and they contain the word
    # TODO, which would make the setup checklist read as permanently unfinished.
    def strip_comments(node):
        if isinstance(node, dict):
            return {k: strip_comments(v) for k, v in node.items()
                    if not k.startswith("$")}
        if isinstance(node, list):
            return [strip_comments(v) for v in node]
        return node

    example = strip_comments(example)

    example["auth"]["authenticated_selector"] = auth_selector or \
        "TODO_CSS_SELECTOR_VISIBLE_ONLY_WHEN_SIGNED_IN"
    if mfa_candidates:
        example["auth"]["mfa_selectors"] = [c["selector"] for c in mfa_candidates[:3]]

    slug = cfg.report_slug or "report_one"
    report = example["reports"].pop("TODO_REPORT_SLUG", {})
    report["enabled"] = True
    report["navigation"] = {"mode": "direct_url", "direct_url": report_url}
    report["filters"] = []
    report["export"] = ({"selector": export_selector} if export_selector
                        else {"selector": "TODO_CSS_SELECTOR_FOR_EXPORT_CONTROL"})
    report.pop("apply_filters_control", None)
    example["reports"] = {slug: report}

    out_path.write_text(json.dumps(example, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"  Draft written to {out_path}")
    print()
    remaining = []
    if not auth_selector:
        remaining.append("auth.authenticated_selector")
    if not export_selector:
        remaining.append("the export control selector")
    if not mfa_candidates:
        remaining.append("auth.mfa_selectors (expected — no challenge is on "
                         "screen while you are signed in; fill it from the "
                         "login page, or leave it and the run will still stop "
                         "safely, just less specifically)")
    if remaining:
        print("  Still to fill in by hand:")
        for item in remaining:
            print(f"    - {item}")
    else:
        print("  Everything workflow.json needs was captured.")
    print()
    print("  Review the file, then:")
    print("    cp config/workflow.draft.json config/workflow.json")
    print("    ./.venv/bin/python -m src.main --validate-config")
    print("=" * 70 + "\n")
    return 0
