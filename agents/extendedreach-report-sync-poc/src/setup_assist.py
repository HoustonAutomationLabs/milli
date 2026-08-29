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


def _frames(page) -> list:
    """Every frame in the page, main document first.

    Lotus Domino applications — which ExtendedReach is built on — put the menu
    and the report content in separate frames. `page.locator()` only searches
    the main document, so on those portals it finds nothing at all and the
    scan looks broken when it is merely looking in the wrong place.
    """
    frames = [page.main_frame]
    for frame in page.frames:
        if frame is not page.main_frame:
            frames.append(frame)
    return frames


def _frame_hint(frame, page) -> Optional[dict[str, str]]:
    """How to find this frame again on a later run.

    A name is stable and readable; a distinctive piece of the URL is the
    fallback. None means the main document, which needs no hint.
    """
    if frame is page.main_frame:
        return None
    if frame.name:
        return {"name": frame.name}
    url = frame.url or ""
    tail = url.rsplit("/", 1)[-1].split("?")[0]
    return {"url_contains": tail} if tail else None


def _scan(page, pattern: re.Pattern[str], roles=("a", "button", "input")) -> list[dict[str, Any]]:
    """Every element whose visible text or accessible attributes match,
    across every frame in the page."""
    found: list[dict[str, Any]] = []
    seen: set[tuple] = set()

    for frame in _frames(page):
        for tag in roles:
            try:
                handles = frame.locator(tag).all()
            except Exception:
                continue                      # a frame can vanish mid-scan
            for handle in handles:
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
                if not described:
                    continue
                described["frame"] = _frame_hint(frame, page)
                key = (described["selector"], str(described["frame"]))
                if key not in seen:
                    seen.add(key)
                    found.append(described)
                if len(found) >= MAX_CANDIDATES:
                    return found
    return found


def _report_page_shape(page) -> str:
    """A one-line description of what is on the page, printed when a scan finds
    nothing. Without it, "no candidate found" gives no clue whether the page
    was empty, framed, or simply worded unexpectedly."""
    parts = []
    for frame in _frames(page):
        try:
            links = frame.locator("a").count()
            buttons = frame.locator("button, input[type=button], input[type=submit]").count()
        except Exception:
            continue
        label = "main page" if frame is page.main_frame else (
            f"frame {frame.name!r}" if frame.name else "unnamed frame")
        parts.append(f"{label}: {links} links, {buttons} buttons")
    return "; ".join(parts) if parts else "nothing readable"


def _choose(candidates: list[dict[str, Any]], what: str, page=None):
    """Print numbered candidates and let the operator pick one.

    Returns (selector, frame_hint), both None if nothing was chosen.
    """
    if not candidates:
        print(f"\n  No obvious candidate found for the {what}.")
        if page is not None:
            print(f"  What this page contains: {_report_page_shape(page)}")
        print("  You will need to find this one in Chrome: right-click the")
        print("  element, Inspect, then right-click the highlighted markup ->")
        print("  Copy -> Copy selector.")
        return None, None

    print(f"\n  Candidates for the {what}:\n")
    for index, item in enumerate(candidates, start=1):
        label = item["text"] or f"<{item['tag']}>"
        where = ""
        if item.get("frame"):
            hint = item["frame"]
            where = f"   [in frame {hint.get('name') or hint.get('url_contains')}]"
        print(f"    {index:2}. {label!r}{where}")
        print(f"        {item['selector']}")

    while True:
        answer = input(f"\n  Which number is the {what}? "
                       "(Enter to skip) ").strip()
        if not answer:
            return None, None
        if answer.isdigit() and 1 <= int(answer) <= len(candidates):
            chosen = candidates[int(answer) - 1]
            return chosen["selector"], chosen.get("frame")
        print("  Not one of the numbers listed.")


def run_setup_assist(cfg, log, out_path: Path, slug: Optional[str] = None,
                     live_path: Optional[Path] = None) -> int:
    """Walk the operator through capturing what workflow.json needs.

    Adds ONE report per run and keeps everything already captured. With nine
    reports to configure, a version that rewrote the file each time would throw
    away the previous eight, and would do it silently.
    """
    from src.browser_worker import BrowserWorker

    slug = (slug or cfg.report_slug or "").strip()

    # Start from what is already configured, so earlier reports survive.
    base_path = None
    for candidate in (live_path, out_path):
        if candidate and candidate.exists():
            base_path = candidate
            break
    if base_path is None:
        base_path = out_path.parent / "workflow.example.json"

    document = json.loads(base_path.read_text(encoding="utf-8"))
    document = _strip_comments(document)
    document.setdefault("reports", {})
    existing = [k for k in document["reports"] if not _PLACEHOLDER_SLUG(k)]

    print("\n" + "=" * 70)
    print("  Setup assistant")
    print()
    print("  This opens a browser and watches. It clicks nothing, downloads")
    print("  nothing, and changes nothing in the portal. You drive.")
    if existing:
        print()
        print(f"  Already configured: {', '.join(existing)}")
        print("  This run adds one more; the others are kept.")
    print("=" * 70)

    if not slug:
        slug = input("\n  Short name for the report you are adding "
                     "(e.g. pastdue_case): ").strip()
    if not slug:
        print("\n  No name given. Nothing was written.\n")
        return 1
    if slug in document["reports"]:
        answer = input(f"\n  {slug!r} is already configured. Replace it? "
                       "(y/N) ").strip().lower()
        if answer != "y":
            print("\n  Left as it was. Nothing was written.\n")
            return 0

    with BrowserWorker(cfg, log, headed=True) as worker:
        page = worker.page
        worker.goto(cfg.base_url)

        # -- step 1: sign in --------------------------------------------
        print("\n  STEP 1 of 3 - Sign in")
        if _is_configured(document.get("auth", {}).get("authenticated_selector")):
            print("  Sign-in was captured on an earlier run. Just sign in if")
            print("  the browser asks; nothing to choose here.")
            input("\n  Press Enter once you can see the home page. ")
            auth_selector = document["auth"]["authenticated_selector"]
            auth_frame = document["auth"].get("authenticated_frame")
        else:
            print("  Sign in in the browser window, including MFA if asked.")
            print("  Nothing here types anything for you.")
            input("\n  Press Enter once you can see the ExtendedReach home page. ")
            signed_in = _scan(page, SIGNED_IN_TEXT)
            auth_selector, auth_frame = _choose(
                signed_in, "element that only appears when you are signed in "
                           "(a Sign Out link is the usual one)", page)

        # -- step 2: the report -----------------------------------------
        print(f"\n  STEP 2 of 3 - Open the report you want to call '{slug}'")
        print("  Navigate to it and apply any filters it should always use.")
        input("\n  Press Enter once the report is on screen. ")

        report_url = page.url
        print(f"\n  Captured report URL:\n    {report_url}")

        # -- step 3: the export control ---------------------------------
        print("\n  STEP 3 of 3 - Identify the export control")
        print("  Do NOT click it. Just identify it below.")
        export_candidates = _scan(page, EXPORT_TEXT)
        export_selector, export_frame = _choose(
            export_candidates, "export/Excel control", page)

        mfa_candidates = _scan(page, MFA_HINT, roles=("input",))

    # -- merge into the document ------------------------------------------
    document.setdefault("auth", {})
    if auth_selector:
        document["auth"]["authenticated_selector"] = auth_selector
        if auth_frame:
            document["auth"]["authenticated_frame"] = auth_frame
    document["auth"].setdefault("login_form_selector", "")
    if mfa_candidates and not _is_configured(
            (document["auth"].get("mfa_selectors") or [None])[0]):
        document["auth"]["mfa_selectors"] = [c["selector"] for c in mfa_candidates[:3]]
    document["auth"].setdefault("captcha_selectors", [
        "iframe[title*='recaptcha' i]", "iframe[src*='hcaptcha' i]"])
    document.setdefault("safety", {
        "url_denylist_substrings": [
            "delete", "remove", "destroy", "edit", "update", "save", "submit",
            "approve", "reject", "create", "new", "insert", "merge", "archive"],
        "screenshot_safe_url_substrings": ["/login", "/signin", "/error", "/denied"],
    })

    # Drop the example's placeholder report the first time a real one is added.
    for key in [k for k in document["reports"] if _PLACEHOLDER_SLUG(k)]:
        document["reports"].pop(key)

    document["reports"][slug] = {
        "enabled": True,
        "description": f"TODO(operator): what {slug} is, in plain words.",
        "navigation": {"mode": "direct_url", "direct_url": report_url},
        "filters": [],
        "export": ({"selector": export_selector, **({"frame": export_frame}
                                                    if export_frame else {})}
                   if export_selector
                   else {"selector": "TODO_CSS_SELECTOR_FOR_EXPORT_CONTROL"}),
        "validation": {
            "expected_csv_headers": [],
        },
    }

    out_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"  Draft written to {out_path}")
    print(f"  Reports now configured: {', '.join(document['reports'])}")
    print()
    remaining = []
    if not auth_selector:
        remaining.append("auth.authenticated_selector")
    if not export_selector:
        remaining.append(f"the export control for {slug}")
    remaining.append(f"reports.{slug}.validation.expected_csv_headers "
                     "(the column names, after you download it once)")
    print("  Still to fill in:")
    for item in remaining:
        print(f"    - {item}")
    print()
    print("  Review the file, then:")
    print(f"    cp {out_path.name} workflow.json      (inside config/)")
    print("    ./.venv/bin/python -m src.main --list-reports")
    print()
    print("  Run this again for the next report.")
    print("=" * 70 + "\n")
    return 0


def _strip_comments(node):
    """Drop the example file's "$comment" guidance.

    Once a field is filled the guidance is only noise, and it contains the word
    TODO, which would make the setup checklist read as permanently unfinished.
    """
    if isinstance(node, dict):
        return {k: _strip_comments(v) for k, v in node.items()
                if not k.startswith("$")}
    if isinstance(node, list):
        return [_strip_comments(v) for v in node]
    return node


def _PLACEHOLDER_SLUG(key: str) -> bool:
    return "TODO" in str(key).upper()


def _is_configured(value) -> bool:
    return bool(value) and "TODO" not in str(value).upper()
