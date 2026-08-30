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


def _capture_one_report(worker, page, document, slug, cfg, log) -> bool:
    """Record one report: navigate, click export, keep what happened.

    Returns True if the report was captured.
    """
    from . import recorder
    from .validators import read_csv_header

    print(f"\n  {'=' * 66}")
    print(f"  Recording: {slug}")
    print(f"  {'=' * 66}")
    print("\n  1. In the browser, open the report you want to call "
          f"'{slug}'.")
    print("     Apply any filters it should always use.")
    input("\n     Press Enter once the report is on screen. ")

    report_url = page.url
    print(f"\n     Captured address:\n       {report_url}")

    print("\n  2. Now CLICK THE EXPORT BUTTON yourself, as you normally would.")
    print("     This one you do click — I watch which button it was and catch")
    print("     the file. A real report downloads; that is expected, and it is")
    print("     how the column names get filled in.")

    context = worker.context
    while True:
        recorder.clear_clicks(context)
        worker.clear_downloads()   # else a previous report's file counts here
        download = None
        print("\n     Click it now. Then come back here.")
        input("     Press Enter once you have clicked (and any download finished). ")

        # Downloads are collected on the context, so one that lands in a new
        # window still counts.
        download = worker.take_download()
        click = recorder.last_click(context)

        if click or download:
            break

        print("\n     I did not see a click or a download.")
        print(f"     What is open: {recorder.describe_surfaces(context)}")
        print("     If the export opened a new window, click the button in")
        print("     THAT window and try again.")
        if input("     Try again for this report? (Y/n) ").strip().lower() == "n":
            print("     Skipping this one; nothing saved for it.")
            return False

    headers: list[str] = []
    extension = "csv"
    if download is not None:
        suggested = download.suggested_filename or ""
        extension = (suggested.rsplit(".", 1)[-1] or "csv").lower()
        saved = cfg.download_dir / f"setup_{slug}.{extension}"
        saved.parent.mkdir(parents=True, exist_ok=True)
        try:
            download.save_as(str(saved))
            print(f"     Downloaded: {saved.name}")
            if extension == "csv":
                headers = read_csv_header(saved, cfg.csv_encodings)
                if headers:
                    print(f"     Column names captured: {len(headers)}")
        except Exception:
            print("     The file could not be saved; column names not captured.")

    export: dict[str, Any] = {}
    if click:
        export["selector"] = click["selector"]
        if click["frame"]:
            export["frame"] = click["frame"]
    else:
        export["selector"] = "TODO_CSS_SELECTOR_FOR_EXPORT_CONTROL"

    document["reports"][slug] = {
        "enabled": True,
        "description": f"TODO(operator): what {slug} is, in plain words.",
        "navigation": {"mode": "direct_url", "direct_url": report_url},
        "filters": [],
        "export": export,
        "validation": {
            "expected_extension": extension,
            "expected_csv_headers": headers,
        },
    }
    return True


def run_setup_assist(cfg, log, out_path: Path, slug: Optional[str] = None,
                     live_path: Optional[Path] = None) -> int:
    """Record each report by watching the operator use the portal.

    Adds reports to whatever is already configured and never rewrites the file
    from scratch, so a second run cannot discard the first.
    """
    from . import recorder
    from src.browser_worker import BrowserWorker

    base_path = None
    for candidate in (live_path, out_path):
        if candidate and candidate.exists():
            base_path = candidate
            break
    if base_path is None:
        base_path = out_path.parent / "workflow.example.json"

    document = _strip_comments(json.loads(base_path.read_text(encoding="utf-8")))
    document.setdefault("reports", {})
    existing = [k for k in document["reports"] if not _PLACEHOLDER_SLUG(k)]

    print("\n" + "=" * 70)
    print("  Setup — recording mode")
    print()
    print("  You drive the browser. I watch which buttons you press and catch")
    print("  the files. Nothing is clicked for you, and nothing in the portal")
    print("  is changed.")
    if existing:
        print()
        print(f"  Already configured: {', '.join(existing)}")
    print("=" * 70)

    captured: list[str] = []
    with BrowserWorker(cfg, log, headed=True) as worker:
        page = worker.page
        # Arm at the context level so new tabs and popups are covered too:
        # this portal opens exports in a new window, and a page-level script
        # never reaches it.
        recorder.install(worker.context)
        worker.goto(cfg.base_url)

        print("\n  STEP 1 — Sign in")
        print("  Sign in in the browser window, including MFA if asked.")
        print("  Nothing here types anything for you.")
        input("\n  Press Enter once you are signed in. ")

        if recorder.has_visible_password(page):
            print("\n  A password field is still showing. If you are signed in,")
            print("  carry on anyway; otherwise finish signing in first.")
            input("  Press Enter to continue. ")

        # No sign-in selector is captured on purpose: the check is the absence
        # of a password field, which needs no configuration and works here.
        document.setdefault("auth", {})
        # Overwrite, not setdefault: the example ships a TODO placeholder here,
        # and setdefault leaves an existing value alone — so the placeholder
        # survived every recording session and failed validation afterwards.
        # An empty value is the supported default: the session check is the
        # absence of a password field.
        current = str(document["auth"].get("authenticated_selector") or "")
        if not current or "TODO" in current.upper():
            document["auth"]["authenticated_selector"] = ""
        document["auth"].setdefault("login_form_selector", "input[type=password]")
        document["auth"].setdefault("mfa_selectors", [])
        document["auth"].setdefault("captcha_selectors", [
            "iframe[title*='recaptcha' i]", "iframe[src*='hcaptcha' i]"])
        document.setdefault("safety", {
            "url_denylist_substrings": [
                "delete", "remove", "destroy", "edit", "update", "save",
                "submit", "approve", "reject", "create", "new", "insert",
                "merge", "archive"],
            "screenshot_safe_url_substrings": [
                "/login", "/signin", "/error", "/denied"],
        })

        # Drop the example's placeholder report once a real one is added.
        for key in [k for k in document["reports"] if _PLACEHOLDER_SLUG(k)]:
            document["reports"].pop(key)

        print("\n  STEP 2 — Record your reports")
        print("  One sign-in covers all of them; stay in this window.")

        next_slug = (slug or cfg.report_slug or "").strip()
        while True:
            if not next_slug:
                next_slug = input(
                    "\n  Short name for the next report "
                    "(e.g. open_beds), or Enter to finish: ").strip()
            if not next_slug:
                break
            if next_slug in document["reports"]:
                answer = input(f"  {next_slug!r} is already configured. "
                               "Replace it? (y/N) ").strip().lower()
                if answer != "y":
                    next_slug = ""
                    continue
            if _capture_one_report(worker, page, document, next_slug, cfg, log):
                captured.append(next_slug)
            next_slug = ""

    out_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"  Draft written to {out_path}")
    if captured:
        print(f"  Recorded this run: {', '.join(captured)}")
    print(f"  Reports now configured: {', '.join(document['reports']) or 'none'}")
    print()
    unfinished = [k for k, v in document["reports"].items()
                  if "TODO" in json.dumps(v)]
    if unfinished:
        print(f"  Still needing attention: {', '.join(unfinished)}")
        print()
    print("  Next:")
    print(f"    cp {out_path} {out_path.parent / 'workflow.json'}")
    print("    ./.venv/bin/python -m src.main --list-reports")
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
