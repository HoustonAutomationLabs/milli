"""Playwright navigation and download. Read-only by construction.

What this module will not do, and why:

* It never types a credential, never fills an MFA code, never touches a
  CAPTCHA. If a challenge appears the run stops with requires_human_login and
  a human finishes sign-in in the headed window.
* It executes only the actions in `config.READ_ONLY_ACTIONS`, and refuses any
  URL containing a substring from the workflow's `url_denylist_substrings`.
  Together these mean a misconfigured workflow file cannot make the tool
  create, edit, approve, reject or delete anything in the portal.
* It reads no page text into logs. The authenticated check asks whether a
  selector exists, not what the page says.

Waits are Playwright's own (`wait_for_selector`, `expect_download`,
`wait_for_load_state`). The single `time.sleep` is a short settle after
filters are applied, where there is no event to wait on.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

from playwright.sync_api import (
    Download,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeout,
    sync_playwright,
)

from .config import AppConfig, READ_ONLY_ACTIONS
from .logging_utils import safe_url
from .validators import build_filename, normalise_extension

# Error categories raised from this module. Fixed vocabulary; no page text.
CATEGORY_NAV_FAILED = "navigation_failed"
CATEGORY_NOT_AUTHENTICATED = "not_authenticated"
CATEGORY_MFA_REQUIRED = "mfa_or_challenge_present"
CATEGORY_EXPORT_CONTROL = "export_control_not_found"
CATEGORY_DOWNLOAD_TIMEOUT = "download_timeout"
CATEGORY_FILTER_REJECTED = "filter_value_rejected"
CATEGORY_BLOCKED_URL = "url_blocked_by_read_only_guard"
CATEGORY_PORTAL_CHANGED = "portal_structure_changed"
CATEGORY_BROWSER_FAILED = "browser_launch_failed"


class BrowserWorkerError(Exception):
    """Carries a category, never a page-derived message."""

    def __init__(self, category: str, detail: str = ""):
        super().__init__(f"{category}: {detail}" if detail else category)
        self.category = category
        self.detail = detail


class RequiresHumanLogin(BrowserWorkerError):
    """Sign-in, MFA or a challenge needs a person. Not a failure — a pause."""


@dataclass
class DownloadResult:
    path: Path
    filename: str
    extension: str
    suggested_extension: str


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def assert_url_allowed(url: str, denylist: list[str]) -> None:
    """Refuse any URL that looks like a write action.

    Crude on purpose. A false positive costs a config edit; a false negative
    could mean this tool submitting or deleting a record in a live system.
    """
    lowered = (url or "").lower()
    for token in denylist or []:
        if token and token.lower() in lowered:
            raise BrowserWorkerError(
                CATEGORY_BLOCKED_URL,
                f"target URL contains {token!r}, which the read-only guard blocks")


def assert_action_allowed(action: str) -> None:
    if action not in READ_ONLY_ACTIONS:
        raise BrowserWorkerError(
            CATEGORY_BLOCKED_URL,
            f"workflow step {action!r} is not in the read-only action set")


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class BrowserWorker:
    """Wraps a persistent Chromium context for one run."""

    def __init__(self, cfg: AppConfig, logger, headed: bool = True):
        self.cfg = cfg
        self.log = logger
        self.headed = headed
        self._playwright = None
        self._context = None
        self.page: Optional[Page] = None

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> "BrowserWorker":
        self.cfg.browser_profile_dir.mkdir(parents=True, exist_ok=True)
        self.cfg.download_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._playwright = sync_playwright().start()
            launch_options = dict(
                user_data_dir=str(self.cfg.browser_profile_dir),
                headless=not self.headed,
                accept_downloads=True,
                downloads_path=str(self.cfg.download_dir),
                args=["--disable-background-networking"],
            )
            # Drive an already-installed browser when one is configured.
            # Playwright stopped building its own Chromium for older macOS
            # releases, and on those the installed Google Chrome is the only
            # way through. It is the same engine either way.
            if self.cfg.browser_channel:
                launch_options["channel"] = self.cfg.browser_channel
            self._context = self._playwright.chromium.launch_persistent_context(
                **launch_options)
        except PlaywrightError as exc:
            detail = ("chromium did not start; run the installer again"
                      if not self.cfg.browser_channel else
                      f"the '{self.cfg.browser_channel}' browser did not start; "
                      "check it is installed in your Applications folder")
            raise BrowserWorkerError(CATEGORY_BROWSER_FAILED, detail) from None
        self._context.set_default_timeout(self.cfg.nav_timeout_ms)
        self.page = (self._context.pages[0] if self._context.pages
                     else self._context.new_page())
        self.log.info("Browser started (headed=%s, profile outside repo)", self.headed)
        return self

    def __exit__(self, *exc_info) -> None:
        try:
            if self._context:
                self._context.close()
        finally:
            if self._playwright:
                self._playwright.stop()

    # -- navigation --------------------------------------------------------

    def goto(self, url: str) -> None:
        target = urljoin(self.cfg.base_url, url)
        assert_url_allowed(target, self.cfg.safety.get("url_denylist_substrings", []))
        self.log.info("Navigating to %s", safe_url(target))
        try:
            self.page.goto(target, wait_until="domcontentloaded",
                           timeout=self.cfg.nav_timeout_ms)
        except PlaywrightTimeout:
            raise BrowserWorkerError(CATEGORY_NAV_FAILED,
                                     "page did not load before the timeout") from None

    # -- authentication ----------------------------------------------------

    def _frame_for(self, spec: Optional[dict[str, Any]]):
        """The frame an element lives in, or the page itself.

        ExtendedReach is a Lotus Domino application and puts its menu and its
        report content in separate frames. An element inside one is invisible
        to a locator on the main document, so anything that came from a frame
        has to be looked for in that frame.
        """
        hint = (spec or {}).get("frame") or {}
        if not hint:
            return self.page

        name = hint.get("name")
        url_part = hint.get("url_contains")
        for frame in self.page.frames:
            if name and frame.name == name:
                return frame
            if url_part and url_part in (frame.url or ""):
                return frame

        raise BrowserWorkerError(
            CATEGORY_PORTAL_CHANGED,
            "the frame the export control lives in was not found; the portal "
            "layout may have changed, or the page may not have finished loading")

    def _selector_present(self, selector: Optional[str], timeout_ms: int = 3000,
                          frame_spec: Optional[dict[str, Any]] = None) -> bool:
        """Existence check only. Reads no text off the page."""
        if not selector:
            return False
        try:
            root = self._frame_for(frame_spec)
            root.wait_for_selector(selector, state="attached", timeout=timeout_ms)
            return True
        except (PlaywrightTimeout, PlaywrightError, BrowserWorkerError):
            return False

    def detect_challenge(self) -> Optional[str]:
        """Return a category if an MFA or CAPTCHA challenge is on screen."""
        auth = self.cfg.auth
        for selector in auth.get("captcha_selectors", []) or []:
            if selector and "TODO" not in selector and self._selector_present(selector, 1500):
                return CATEGORY_MFA_REQUIRED
        for selector in auth.get("mfa_selectors", []) or []:
            if selector and "TODO" not in selector and self._selector_present(selector, 1500):
                return CATEGORY_MFA_REQUIRED
        return None

    def is_authenticated(self) -> bool:
        return self._selector_present(
            self.cfg.auth.get("authenticated_selector"),
            timeout_ms=5000,
            frame_spec={"frame": self.cfg.auth.get("authenticated_frame")})

    def ensure_authenticated(self) -> None:
        """Check the session; in headed mode, wait for a human to sign in.

        Never fills a username, a password, an MFA code or a CAPTCHA. The
        operator does all of it in the window this opened.
        """
        self.goto(self.cfg.base_url)

        if self.is_authenticated():
            self.log.info("Existing session is authenticated")
            return

        challenge = self.detect_challenge()
        if challenge:
            self.log.warning("A sign-in challenge is present; it will not be automated")

        if not self.headed:
            raise RequiresHumanLogin(
                CATEGORY_NOT_AUTHENTICATED,
                "no authenticated session and the browser is headless; "
                "re-run headed so a person can sign in")

        # Headed: hand the window to the operator.
        print("\n" + "=" * 68, flush=True)
        print("  Sign-in required.", flush=True)
        print("  Complete sign-in and MFA yourself in the browser window.", flush=True)
        print("  This tool will not type credentials or codes for you.", flush=True)
        print(f"  Waiting up to {self.cfg.login_wait_seconds}s, then continuing "
              f"automatically once you are signed in.", flush=True)
        print("=" * 68 + "\n", flush=True)

        selector = self.cfg.auth.get("authenticated_selector")
        try:
            root = self._frame_for({"frame": self.cfg.auth.get("authenticated_frame")})
            root.wait_for_selector(
                selector, state="attached",
                timeout=self.cfg.login_wait_seconds * 1000)
        except (PlaywrightTimeout, PlaywrightError):
            raise RequiresHumanLogin(
                CATEGORY_NOT_AUTHENTICATED,
                f"still not signed in after {self.cfg.login_wait_seconds}s") from None

        self.log.info("Sign-in completed by the operator; session saved to the profile")

    # -- the report --------------------------------------------------------

    def navigate_to_report(self, report=None) -> None:
        report = report or self.cfg.report
        if report is None:
            raise BrowserWorkerError(CATEGORY_NAV_FAILED, "no report configured")

        # A direct URL from .env wins, but only when a single report is
        # configured: with several, one override would send every report to the
        # same page and quietly produce nine copies of one export.
        single = len(self.cfg.enabled_reports()) == 1
        override = self.cfg.report_url_override if single else None
        url = override or (report.navigation or {}).get("direct_url")
        mode = (report.navigation or {}).get("mode", "direct_url")

        if override or (mode == "direct_url" and url):
            self.goto(url)
        elif mode == "steps":
            for index, step in enumerate((report.navigation or {}).get("steps", [])):
                self._run_step(step, index)
        else:
            raise BrowserWorkerError(CATEGORY_NAV_FAILED,
                                     f"navigation mode {mode!r} has nothing to follow")

        # A report page that no longer matches the workflow file is a portal
        # change, not a transient error, and is reported as such.
        export = report.export or {}
        locator = self._export_locator(export)
        try:
            locator.wait_for(state="visible", timeout=self.cfg.nav_timeout_ms)
        except (PlaywrightTimeout, PlaywrightError):
            raise BrowserWorkerError(
                CATEGORY_PORTAL_CHANGED,
                "the configured export control was not found on the report "
                "page; the portal layout or the workflow file is out of date"
            ) from None

    def _run_step(self, step: dict[str, Any], index: int) -> None:
        action = step.get("action", "")
        assert_action_allowed(action)
        self.log.info("Step %d: %s", index + 1, action)

        if action == "goto":
            self.goto(step.get("url", ""))
        elif action == "click_link":
            name = step.get("name", "")
            link = self._frame_for(step).get_by_role(
                "link", name=name, exact=bool(step.get("exact"))).first
            link.wait_for(state="visible", timeout=self.cfg.nav_timeout_ms)
            link.click()
            self.page.wait_for_load_state("domcontentloaded")
        elif action == "click":
            locator = self._frame_for(step).locator(step["selector"]).first
            locator.wait_for(state="visible", timeout=self.cfg.nav_timeout_ms)
            locator.click()
            self.page.wait_for_load_state("domcontentloaded")
        elif action == "wait_for":
            self._frame_for(step).wait_for_selector(
                step["selector"], state="visible",
                timeout=self.cfg.nav_timeout_ms)
        elif action in {"select_option", "fill_filter", "check", "uncheck"}:
            self._apply_filter_step(step)

    def apply_filters(self, report=None) -> None:
        """Apply the predefined, non-sensitive filters from configuration.

        Values are re-checked here against the same pattern config validation
        used. The check is repeated deliberately: this is the last point
        before text is typed into a live portal.
        """
        report = report or self.cfg.report
        if report is None or not report.filters:
            return

        resolved = self.cfg.filter_values(report)
        applied = 0
        for spec in report.filters:
            name = spec.get("name", "")
            if name not in resolved:
                if spec.get("required"):
                    raise BrowserWorkerError(
                        CATEGORY_FILTER_REJECTED,
                        f"required filter {name!r} has no valid configured value")
                continue
            self._apply_filter_step(spec, resolved[name])
            applied += 1

        if applied:
            control = report.apply_filters_control or {}
            if control.get("enabled") and control.get("selector"):
                locator = self.page.locator(control["selector"]).first
                locator.wait_for(state="visible", timeout=self.cfg.nav_timeout_ms)
                locator.click()
                self.page.wait_for_load_state("networkidle")
            else:
                # No event to wait on when filters apply on change: a short
                # settle is the honest fallback.
                time.sleep(1.0)
            self.log.info("Applied %d predefined filter(s)", applied)

    def _apply_filter_step(self, spec: dict[str, Any],
                           value: Optional[str] = None) -> None:
        from .config import FILTER_VALUE_PATTERN

        selector = spec.get("selector")
        if not selector:
            raise BrowserWorkerError(CATEGORY_FILTER_REJECTED,
                                     "filter step has no selector")
        kind = spec.get("type") or spec.get("action") or "fill_filter"

        if value is None:
            import os
            value = os.getenv(spec.get("value_env", ""), "").strip()

        if kind in {"select_option", "fill_filter"}:
            if not value or not FILTER_VALUE_PATTERN.match(value):
                raise BrowserWorkerError(
                    CATEGORY_FILTER_REJECTED,
                    "filter value rejected by the non-sensitive pattern; this "
                    "guard keeps names and free text out of portal fields")

        locator = self._frame_for(spec).locator(selector).first
        locator.wait_for(state="visible", timeout=self.cfg.nav_timeout_ms)

        if kind == "select_option":
            locator.select_option(label=value)
        elif kind == "fill_filter":
            locator.fill(value)
        elif kind == "check":
            locator.check()
        elif kind == "uncheck":
            locator.uncheck()

    # -- download ----------------------------------------------------------

    def _export_locator(self, export: dict[str, Any]):
        root = self._frame_for(export)
        if export.get("selector"):
            return root.locator(export["selector"]).first
        role = export.get("role", "button")
        name = export.get("name", "")
        return root.get_by_role(role, name=name).first

    def download_report(self, report=None,
                        when: Optional[datetime] = None) -> DownloadResult:
        """Click the export control and save the download under our own name."""
        report = report or self.cfg.report
        if report is None:
            raise BrowserWorkerError(CATEGORY_EXPORT_CONTROL, "no report configured")
        export = report.export or {}
        locator = self._export_locator(export)

        try:
            locator.wait_for(state="visible", timeout=self.cfg.nav_timeout_ms)
        except (PlaywrightTimeout, PlaywrightError):
            raise BrowserWorkerError(CATEGORY_EXPORT_CONTROL,
                                     "export control not visible") from None

        self.log.info("Triggering export")
        try:
            with self.page.expect_download(
                    timeout=self.cfg.download_timeout_ms) as download_info:
                locator.click()
            download: Download = download_info.value
        except PlaywrightTimeout:
            raise BrowserWorkerError(
                CATEGORY_DOWNLOAD_TIMEOUT,
                "no download started before the timeout") from None

        # Do not assume the extension from the button label. In this agency's
        # portal the control is labelled "Excel" on reports that emit CSV;
        # saving a CSV as .xlsx would fail validation for the wrong reason.
        suggested = download.suggested_filename or ""
        suggested_ext = normalise_extension(Path(suggested).suffix) or "xlsx"
        declared = normalise_extension(
            (report.validation or {}).get("expected_extension", "")) or suggested_ext
        if declared and declared != suggested_ext:
            self.log.warning(
                "Download extension is '%s' but the workflow file expects '%s'; "
                "using the actual one", suggested_ext, declared)

        filename = build_filename(report.slug, suggested_ext, when)
        destination = self.cfg.download_dir / filename
        download.save_as(str(destination))
        self.log.info("Saved download as %s", filename)

        return DownloadResult(
            path=destination,
            filename=filename,
            extension=suggested_ext,
            suggested_extension=suggested_ext,
        )

    # -- diagnostics -------------------------------------------------------

    def capture_failure_diagnostic(self, report_slug: str = "run",
                                   when: Optional[datetime] = None) -> Optional[Path]:
        """Opt-in screenshot, only on a page the workflow marks safe.

        A screenshot of a report page is a screenshot of case data, so the
        default outcome on a report page is *no image*: the caller gets None
        and the run log records the redacted URL path instead.
        """
        if not self.cfg.screenshot_on_failure:
            return None
        if not self.page:
            return None

        current = safe_url(self.page.url)
        safe_patterns = self.cfg.safety.get("screenshot_safe_url_substrings", [])
        on_safe_surface = any(p.lower() in current.lower() for p in safe_patterns if p)

        # A page where we are not signed in cannot be showing case data.
        if not on_safe_surface and self.is_authenticated():
            self.log.warning(
                "Screenshot skipped: the page is not on a screenshot-safe "
                "surface and may show case data (url path %s)", current)
            return None

        self.cfg.screenshot_dir.mkdir(parents=True, exist_ok=True)
        when = when or datetime.now()
        path = self.cfg.screenshot_dir / (
            f"failure_{report_slug}_{when.strftime('%Y-%m-%d_%H%M%S')}.png")
        try:
            self.page.screenshot(path=str(path), full_page=False)
        except PlaywrightError:
            return None
        try:
            path.chmod(0o600)
        except OSError:
            pass
        self.log.info("Saved failure screenshot (local only, never uploaded)")
        return path
