"""Record what the operator clicks, instead of guessing which element to click.

Pattern-matching for a control labelled "Excel" fails on this portal: it is a
Lotus Domino application, so the toolbar lives in a frame, and the export
control turned out to be an icon with no id and no text. Nothing to match on.

Recording sidesteps all of it. The operator clicks the button they already
click every day; a listener in every frame notes which element received the
click and Playwright catches the download that follows. The selector is a fact
about a real click rather than an inference, which is also what keeps this
deterministic — no model looks at the page.

The listener stores its result on `window` synchronously and Python reads it
back afterwards. An async callback into Python loses the race against the
download navigation and the click is silently lost — verified, not assumed.
"""

from __future__ import annotations

from typing import Any, Optional

# A script BODY, not a function: Playwright's Python `add_init_script` executes
# what it is given. Passing "() => {...}" defines a function and never calls
# it, so the listener is never installed and every click is missed — which
# looks identical to the portal being unrecordable.
RECORDER_SCRIPT = """
if (!window.__erInstalled) {
  window.__erInstalled = true;
  var cssPath = function (el) {
    if (el.id) return '#' + CSS.escape(el.id);
    var cls = Array.prototype.slice.call(el.classList || []);
    for (var i = 0; i < cls.length; i++) {
      var s = el.tagName.toLowerCase() + '.' + CSS.escape(cls[i]);
      try { if (document.querySelectorAll(s).length === 1) return s; } catch (e) {}
    }
    var parts = [], n = el;
    while (n && n.nodeType === 1 && parts.length < 6) {
      var p = n.tagName.toLowerCase(), par = n.parentElement;
      if (par) {
        var sib = Array.prototype.slice.call(par.children)
                    .filter(function (c) { return c.tagName === n.tagName; });
        if (sib.length > 1) p += ':nth-of-type(' + (sib.indexOf(n) + 1) + ')';
      }
      parts.unshift(p);
      if (n.id) { parts[0] = '#' + CSS.escape(n.id); break; }
      n = n.parentElement;
    }
    return parts.join(' > ');
  };
  document.addEventListener('click', function (e) {
    var el = (e.target.closest && e.target.closest('a,button,input,[onclick]'))
             || e.target;
    window.__erLastClick = {
      selector: cssPath(el),
      tag: el.tagName.toLowerCase(),
      at: Date.now()
    };
  }, true);
}
"""


def install(target) -> None:
    """Arm the recorder. Must be called before navigating.

    Prefer passing the browser *context*, not a page: a context-level init
    script reaches every page it opens, including new tabs and popups. Domino
    commonly opens an export in a new window, and a page-level script never
    reaches it — the click is simply never seen, which is indistinguishable
    from the operator not having clicked.
    """
    target.add_init_script(RECORDER_SCRIPT)


def _pages(target) -> list:
    """Every page to inspect: a context's pages, or the single page given."""
    pages = getattr(target, "pages", None)
    return list(pages) if pages is not None else [target]


def frame_hint(frame, page) -> Optional[dict[str, str]]:
    """How to find this frame again on a later run.

    A name where the frame has one; otherwise a distinctive piece of its URL.
    Domino frames are frequently unnamed, so the URL fallback is the common
    case rather than the exception. None means the main document.
    """
    if frame is page.main_frame:
        return None
    if frame.name:
        return {"name": frame.name}
    tail = (frame.url or "").rsplit("/", 1)[-1].split("?")[0]
    return {"url_contains": tail} if tail else None


def last_click(target) -> Optional[dict[str, Any]]:
    """The most recent click across every frame, with its frame hint.

    Returns None if nothing was clicked, which is a real answer: it means the
    export control was never pressed, or pressing it did not dispatch a click
    we can see.
    """
    best = None
    for page in _pages(target):
        for frame in page.frames:
            try:
                got = frame.evaluate("window.__erLastClick || null")
            except Exception:
                continue                  # a frame can navigate away mid-read
            if got and (best is None or got["at"] > best[0]["at"]):
                best = (got, frame, page)

    if best is None:
        return None
    click, frame, page = best
    return {
        "selector": click["selector"],
        "tag": click["tag"],
        "frame": frame_hint(frame, page),
        "frame_label": frame.name or (frame.url or "").rsplit("/", 1)[-1],
    }


def clear_clicks(target) -> None:
    """Forget any earlier click, so one recording cannot pick up the last."""
    for page in _pages(target):
        for frame in page.frames:
            try:
                frame.evaluate("window.__erLastClick = null")
            except Exception:
                continue


def describe_surfaces(target) -> str:
    """What is open right now, for when nothing was recorded.

    "No click seen" on its own gives no clue whether the export opened a new
    window, whether the page was framed, or whether the button was simply
    never pressed.
    """
    parts = []
    for index, page in enumerate(_pages(target), start=1):
        frames = len(page.frames)
        tail = (page.url or "").rsplit("/", 1)[-1].split("?")[0] or "(blank)"
        parts.append(f"window {index}: {tail}, {frames} frame(s)")
    return "; ".join(parts) if parts else "nothing open"


def has_visible_password(target) -> bool:
    """Whether a password field is visible in any frame.

    This is the sign-in test. A negative check needs no configuration at all,
    where a positive one ("find the Sign Out link") has to be captured per
    portal and could not be captured on this one. Every sign-in page has a
    password field; no signed-in page does.
    """
    for page in _pages(target):
        for frame in page.frames:
            try:
                fields = frame.locator("input[type=password]")
                for index in range(fields.count()):
                    if fields.nth(index).is_visible():
                        return True
            except Exception:
                continue
    return False
