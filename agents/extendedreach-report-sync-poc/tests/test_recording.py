"""Browser tests for the click recorder, against a Domino-shaped page.

These drive a real browser. That is the point: the portal work went wrong five
times because it was reasoned about rather than run. The fixture reproduces
what defeated the previous approach — a frameset, an unnamed content frame, and
an export control that is an icon with no id and no text to match on.

Skipped automatically where no browser is available, so the suite still passes
on a machine that has not downloaded one.
"""

from __future__ import annotations

import csv

import pytest

from src import recorder

playwright_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def browser():
    """A real browser, or skip. Never fail the suite for a missing browser."""
    with playwright_api.sync_playwright() as p:
        try:
            launched = p.chromium.launch(headless=True)
        except Exception as exc:                      # no browser downloaded
            pytest.skip(f"no browser available: {type(exc).__name__}")
        yield launched
        launched.close()


@pytest.fixture()
def portal(tmp_path):
    """A miniature Lotus Domino application.

    Menu in a named frame, content in an unnamed one, and the export control an
    icon-only link — the shape that made pattern matching find nothing at all.
    """
    with (tmp_path / "openbeds.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Home", "County", "Beds Open", "Last Updated"])
        writer.writerow(["Sample Home A", "Harris", "3", "2026-08-29"])

    (tmp_path / "app.html").write_text(
        '<html><frameset cols="25%,75%">'
        '<frame name="NotesView" src="menu.html">'
        '<frame src="body.html">'
        '</frameset></html>', encoding="utf-8")
    (tmp_path / "menu.html").write_text(
        '<html><body><a href="#" id="nav">Open Beds</a></body></html>',
        encoding="utf-8")
    (tmp_path / "body.html").write_text(
        '<html><body><table><tr><td>Sample Home A</td><td>3</td></tr></table>'
        '<a href="openbeds.csv" download class="tb x1">'
        '<img alt="" style="width:32px;height:32px;background:#888"></a>'
        '</body></html>', encoding="utf-8")
    (tmp_path / "login.html").write_text(
        '<html><body><form><input type="text" name="u">'
        '<input type="password" name="p"></form></body></html>',
        encoding="utf-8")
    return tmp_path


@pytest.fixture()
def page(browser, portal):
    ctx = browser.new_context(accept_downloads=True)
    pg = ctx.new_page()
    recorder.install(pg)
    yield pg
    ctx.close()


# -- the sign-in test needs no configuration --------------------------------

def test_a_sign_in_page_is_recognised_by_its_password_field(page, portal):
    page.goto(f"file://{portal}/login.html")
    assert recorder.has_visible_password(page) is True


def test_a_signed_in_page_has_no_password_field(page, portal):
    page.goto(f"file://{portal}/app.html")
    assert recorder.has_visible_password(page) is False


# -- recording ---------------------------------------------------------------

def test_the_init_script_reaches_every_frame(page, portal):
    """A script body, not a function: passing an arrow function defines it and
    never calls it, so no listener is installed and every click is missed."""
    page.goto(f"file://{portal}/app.html")
    assert len(page.frames) == 3
    for frame in page.frames:
        assert frame.evaluate("window.__erInstalled || false") is True


def test_a_click_inside_a_frame_is_recorded_with_its_selector(page, portal):
    page.goto(f"file://{portal}/app.html")
    target = next(f for f in page.frames if f.locator("a.tb").count())
    target.locator("a.tb").click()

    click = recorder.last_click(page)
    assert click is not None
    assert click["selector"] == "a.tb"
    assert click["tag"] == "a"


def test_an_unnamed_frame_is_identified_by_its_url(page, portal):
    """Domino frames are frequently unnamed, so the URL fallback is the common
    case rather than the exception."""
    page.goto(f"file://{portal}/app.html")
    target = next(f for f in page.frames if f.locator("a.tb").count())
    target.locator("a.tb").click()

    hint = recorder.last_click(page)["frame"]
    assert hint == {"url_contains": "body.html"}


def test_a_click_in_a_named_frame_records_the_name(page, portal):
    page.goto(f"file://{portal}/app.html")
    menu = next(f for f in page.frames if f.name == "NotesView")
    menu.locator("#nav").click()
    assert recorder.last_click(page)["frame"] == {"name": "NotesView"}


def test_nothing_clicked_reports_nothing(page, portal):
    """A real answer, not a failure: it means the export was never pressed."""
    page.goto(f"file://{portal}/app.html")
    assert recorder.last_click(page) is None


def test_clearing_forgets_an_earlier_click(page, portal):
    """Otherwise recording a second report picks up the first one's button."""
    page.goto(f"file://{portal}/app.html")
    next(f for f in page.frames if f.locator("a.tb").count()).locator("a.tb").click()
    assert recorder.last_click(page) is not None

    recorder.clear_clicks(page)
    assert recorder.last_click(page) is None


# -- the download, and the columns it hands us -------------------------------

def test_the_export_download_is_caught_and_its_columns_read(page, portal, tmp_path):
    """The recorded click produces a real file, so the expected column names
    come from the export itself instead of being typed in by hand."""
    from src.validators import read_csv_header

    page.goto(f"file://{portal}/app.html")
    target = next(f for f in page.frames if f.locator("a.tb").count())
    with page.expect_download(timeout=15_000) as info:
        target.locator("a.tb").click()
    download = info.value

    saved = tmp_path / "captured.csv"
    download.save_as(str(saved))
    assert download.suggested_filename == "openbeds.csv"
    assert read_csv_header(saved) == ["Home", "County", "Beds Open", "Last Updated"]


def test_the_recorded_selector_finds_the_element_again(page, portal):
    """The whole point: the recorded selector must work on a later run."""
    page.goto(f"file://{portal}/app.html")
    target = next(f for f in page.frames if f.locator("a.tb").count())
    target.locator("a.tb").click()
    click = recorder.last_click(page)

    page.goto(f"file://{portal}/app.html")          # fresh load, as a run would
    hint = click["frame"]
    found = [f for f in page.frames if hint["url_contains"] in (f.url or "")]
    assert len(found) == 1
    assert found[0].locator(click["selector"]).count() == 1


# -- exports that open a new window -----------------------------------------

@pytest.fixture()
def popup_portal(tmp_path):
    """A portal whose export opens in a new window, as Domino often does."""
    with (tmp_path / "openbeds.csv").open("w", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["Home", "County", "Beds Open"])
        w.writerow(["Sample Home A", "Harris", "3"])
    (tmp_path / "app.html").write_text(
        '<html><frameset cols="25%,75%">'
        '<frame name="NotesView" src="menu.html">'
        '<frame src="body.html">'
        '</frameset></html>', encoding="utf-8")
    (tmp_path / "menu.html").write_text('<html><body>menu</body></html>',
                                        encoding="utf-8")
    # The export opens a popup, which then downloads.
    (tmp_path / "body.html").write_text(
        '<html><body><a id="xl" href="popup.html" target="_blank">Excel</a>'
        '</body></html>', encoding="utf-8")
    (tmp_path / "popup.html").write_text(
        '<html><body><a id="inner" href="openbeds.csv" download>Download</a>'
        '</body></html>', encoding="utf-8")
    return tmp_path


def test_a_click_in_a_popup_window_is_still_recorded(browser, popup_portal):
    """The bug this covers: the recorder was attached to a single page, so an
    export that opened a new window was never seen and the run silently
    recorded nothing — indistinguishable from the operator not clicking."""
    ctx = browser.new_context(accept_downloads=True)
    recorder.install(ctx)                     # context-level, not page-level
    page = ctx.new_page()
    page.goto(f"file://{popup_portal}/app.html")

    frame = next(f for f in page.frames if f.locator("#xl").count())
    with ctx.expect_page() as popup_info:
        frame.locator("#xl").click()
    popup = popup_info.value
    popup.wait_for_load_state()
    assert len(ctx.pages) == 2

    # The click that matters happens in the NEW window.
    recorder.clear_clicks(ctx)
    popup.locator("#inner").click()

    click = recorder.last_click(ctx)
    assert click is not None, "a click in a second window was not seen"
    assert click["selector"] == "#inner"
    ctx.close()


def test_surfaces_are_described_when_nothing_was_recorded(browser, popup_portal):
    """So a failed capture says what was open, instead of just "nothing"."""
    ctx = browser.new_context(accept_downloads=True)
    recorder.install(ctx)
    page = ctx.new_page()
    page.goto(f"file://{popup_portal}/app.html")

    assert recorder.last_click(ctx) is None
    described = recorder.describe_surfaces(ctx)
    assert "window 1" in described
    assert "frame(s)" in described
    ctx.close()
