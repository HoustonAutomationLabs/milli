"""Frame resolution — the portal is a Lotus Domino app and uses framesets."""
import pytest

from src.browser_worker import BrowserWorker, BrowserWorkerError


class FakeFrame:
    def __init__(self, name="", url=""):
        self.name, self.url = name, url


class FakePage:
    def __init__(self, frames):
        self.frames = frames


def _worker(frames):
    w = BrowserWorker.__new__(BrowserWorker)
    w.page = FakePage(frames)
    return w


MAIN = FakeFrame("", "https://portal.example/app.nsf")
MENU = FakeFrame("NotesView", "https://portal.example/app.nsf/menu")
BODY = FakeFrame("", "https://portal.example/app.nsf/reportbody?OpenView")


def test_no_frame_hint_uses_the_main_page():
    w = _worker([MAIN])
    assert w._frame_for({}) is w.page
    assert w._frame_for(None) is w.page
    assert w._frame_for({"frame": None}) is w.page


def test_a_frame_is_found_by_name():
    w = _worker([MAIN, MENU, BODY])
    assert w._frame_for({"frame": {"name": "NotesView"}}) is MENU


def test_a_frame_is_found_by_url_fragment():
    """Domino frames are often unnamed, so a distinctive piece of the URL is
    the only stable handle."""
    w = _worker([MAIN, MENU, BODY])
    assert w._frame_for({"frame": {"url_contains": "reportbody"}}) is BODY


def test_a_missing_frame_is_reported_as_a_portal_change():
    w = _worker([MAIN])
    with pytest.raises(BrowserWorkerError) as excinfo:
        w._frame_for({"frame": {"name": "GoneAway"}})
    assert excinfo.value.category == "portal_structure_changed"


def test_the_name_is_preferred_over_a_url_that_also_matches():
    other = FakeFrame("Other", "https://portal.example/app.nsf/reportbody")
    w = _worker([MAIN, other, BODY])
    got = w._frame_for({"frame": {"name": "Other", "url_contains": "reportbody"}})
    assert got is other
