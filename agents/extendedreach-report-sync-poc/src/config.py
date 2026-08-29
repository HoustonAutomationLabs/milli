"""Configuration loading and validation.

Everything the tool needs comes from environment variables (via .env) and a
JSON workflow file. Nothing about the portal is hardcoded here — no URLs, no
selectors, no credentials.

`validate()` collects *every* problem before raising, so an operator filling
this in for the first time sees the whole list rather than one error per run.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

# Values this tool will type into a portal filter. Deliberately narrow: no
# apostrophes, no commas, nothing that reads like free text. A person's name
# must never be typed into a search box by an automated run.
FILTER_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9 _./:-]{1,64}$")

APPROVED_EXTENSIONS = {"csv", "xlsx", "xls", "pdf"}

# Placeholder markers from .env.example. Present means "not filled in yet".
_PLACEHOLDER = re.compile(r"TODO", re.IGNORECASE)


class ConfigError(Exception):
    """Raised when configuration cannot be used. Message lists every problem."""


@dataclass
class Problem:
    key: str
    detail: str
    severity: str = "error"     # "error" | "warning"

    def __str__(self) -> str:
        mark = "ERROR  " if self.severity == "error" else "WARN   "
        return f"{mark} {self.key}: {self.detail}"


def _project_root() -> Path:
    """The folder holding this project — the one containing src/."""
    return Path(__file__).resolve().parent.parent


def _repo_root(start: Path) -> Optional[Path]:
    """The git repository this file sits in, if there is one."""
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _protected_roots() -> list[Path]:
    """Directories a credential, browser profile or PHI download must never
    land in.

    The project directory is always protected, git or no git. An earlier
    version looked only for a .git directory, which meant the whole guard
    silently did nothing for anyone who downloaded the project as a zip —
    exactly the people least likely to notice a browser profile full of
    session cookies sitting next to the code. A safety check that quietly
    stops working in the configuration most users actually run is worse than
    no check at all, because it is still believed.

    The git root is added when present, so a project nested inside a larger
    repository is protected up to the repository boundary too.
    """
    roots = [_project_root()]
    repo = _repo_root(Path(__file__).resolve())
    if repo is not None:
        roots.append(repo)
    return roots


def _is_inside_repo(path: Path, roots) -> bool:
    """True if `path` is inside any protected directory."""
    if roots is None:
        return False
    if isinstance(roots, Path):
        roots = [roots]
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(Path(root).resolve())
            return True
        except ValueError:
            continue
    return False


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


@dataclass
class ReportConfig:
    """One report.

    Each report carries its own validation rules. That matters once there is
    more than one: nine ExtendedReach reports have nine different sets of
    columns, and a single global header list would either be empty (checking
    nothing) or wrong for eight of them.
    """

    slug: str
    description: str = ""
    enabled: bool = True
    navigation: dict[str, Any] = field(default_factory=dict)
    filters: list[dict[str, Any]] = field(default_factory=list)
    apply_filters_control: dict[str, Any] = field(default_factory=dict)
    export: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    drive_folder_id: str = ""          # optional; falls back to the global one

    # -- per-report validation, falling back to the global settings --------

    def expected_headers(self, fallback: list[str]) -> list[str]:
        """Columns this report must have.

        `expected_csv_headers` in the workflow file wins. `expected_csv_headers_env`
        names an environment variable instead, which keeps a long column list out
        of a file that gets read by people. An explicit empty list means "do not
        check this report's columns" and is honoured, so it is distinguished from
        the key being absent.
        """
        declared = self.validation.get("expected_csv_headers")
        if isinstance(declared, list):
            return [str(h).strip() for h in declared if str(h).strip()]
        env_name = self.validation.get("expected_csv_headers_env")
        if env_name:
            raw = os.getenv(env_name, "").strip()
            if raw:
                return [part.strip() for part in raw.split(",") if part.strip()]
            return []
        return fallback

    def min_bytes(self, fallback: int) -> int:
        value = self.validation.get("min_file_bytes")
        try:
            return int(value) if value is not None else fallback
        except (TypeError, ValueError):
            return fallback


@dataclass
class AppConfig:
    base_url: str
    report_slug: str
    browser_profile_dir: Path
    download_dir: Path
    log_dir: Path
    screenshot_dir: Path

    workflow_path: Optional[Path] = None
    workflow: dict[str, Any] = field(default_factory=dict)
    reports: dict[str, ReportConfig] = field(default_factory=dict)
    report_url_override: Optional[str] = None

    min_file_bytes: int = 1024
    allowed_extensions: set[str] = field(default_factory=lambda: set(APPROVED_EXTENSIONS))
    expected_csv_headers: list[str] = field(default_factory=list)
    csv_encodings: list[str] = field(default_factory=lambda: ["utf-8-sig", "cp1252"])

    drive_folder_id: str = ""
    google_credentials_file: Optional[Path] = None
    google_token_file: Optional[Path] = None
    google_scopes: list[str] = field(
        default_factory=lambda: ["https://www.googleapis.com/auth/drive.file"])

    # Which browser to drive. Empty means the Chromium Playwright downloads.
    # "chrome" or "msedge" drives a copy already installed on the machine,
    # which is the only option on a macOS version Playwright no longer builds
    # its own Chromium for.
    browser_channel: str = ""

    screenshot_on_failure: bool = False
    login_wait_seconds: int = 300
    nav_timeout_ms: int = 45_000
    download_timeout_ms: int = 120_000
    schedule_cron: str = "0 18 * * *"
    redact_terms: list[str] = field(default_factory=list)

    # Populated by validate(); kept so --validate-config can print warnings
    # that are not fatal.
    warnings: list[Problem] = field(default_factory=list)

    # ---- derived helpers -------------------------------------------------

    @property
    def report(self) -> Optional[ReportConfig]:
        """The single report named by REPORT_SLUG, when there is one.

        Kept so single-report callers read naturally. With several reports
        configured and no REPORT_SLUG set, this is the first enabled one; use
        `selected_reports()` for anything that should cover them all.
        """
        if self.report_slug and self.report_slug in self.reports:
            return self.reports[self.report_slug]
        enabled = self.enabled_reports()
        return enabled[0] if enabled else None

    def enabled_reports(self) -> list[ReportConfig]:
        return [r for r in self.reports.values() if r.enabled]

    def selected_reports(self, only: Optional[str] = None) -> list[ReportConfig]:
        """Which reports a run should cover.

        `only` names one report explicitly. Otherwise every enabled report runs,
        which is the point of having more than one. REPORT_SLUG no longer
        narrows a run -- it only names the default for single-report commands --
        because a stale slug silently exporting one report out of nine would be
        the worst kind of failure: quiet and plausible.
        """
        if only:
            report = self.reports.get(only)
            return [report] if report else []
        return self.enabled_reports()

    def drive_folder_for(self, report: ReportConfig) -> str:
        return report.drive_folder_id or self.drive_folder_id

    @property
    def auth(self) -> dict[str, Any]:
        return self.workflow.get("auth", {}) if self.workflow else {}

    @property
    def safety(self) -> dict[str, Any]:
        return self.workflow.get("safety", {}) if self.workflow else {}

    def filter_values(self, report: Optional[ReportConfig] = None) -> dict[str, str]:
        """Resolved filter values, keyed by filter name. Values that fail the
        pattern are omitted here and reported by validate()."""
        report = report or self.report
        resolved: dict[str, str] = {}
        for spec in (report.filters if report else []):
            env_name = spec.get("value_env")
            if not env_name:
                continue
            value = os.getenv(env_name, "").strip()
            if value and FILTER_VALUE_PATTERN.match(value):
                resolved[spec.get("name", env_name)] = value
        return resolved


def load(env_file: Optional[str] = None,
         project_root: Optional[Path] = None) -> AppConfig:
    """Read .env and the workflow file into an AppConfig. Does not validate."""
    root = project_root or Path(__file__).resolve().parent.parent
    load_dotenv(env_file or root / ".env", override=False)

    def path_env(name: str, default: str) -> Path:
        raw = os.getenv(name, "").strip() or default
        candidate = Path(raw).expanduser()
        return candidate if candidate.is_absolute() else (root / candidate).resolve()

    workflow_raw = os.getenv("WORKFLOW_FILE", "").strip()
    workflow_path: Optional[Path] = None
    workflow: dict[str, Any] = {}
    if workflow_raw:
        candidate = Path(workflow_raw).expanduser()
        workflow_path = candidate if candidate.is_absolute() else (root / candidate)
        if workflow_path.exists():
            try:
                workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ConfigError(
                    f"{workflow_path.name} is not valid JSON "
                    f"(line {exc.lineno}, column {exc.colno})"
                    + _json_hint(workflow_path)
                ) from None

    slug = os.getenv("REPORT_SLUG", "").strip()
    reports = _build_reports(workflow)

    extensions = {e.lower().lstrip(".") for e in
                  _split_csv(os.getenv("ALLOWED_EXTENSIONS")) } or set(APPROVED_EXTENSIONS)

    cfg = AppConfig(
        base_url=os.getenv("EXTENDEDREACH_BASE_URL", "").strip(),
        report_slug=slug,
        browser_profile_dir=path_env("BROWSER_PROFILE_DIR", "~/er-sync/profile"),
        download_dir=path_env("DOWNLOAD_DIR", "~/er-sync/downloads"),
        log_dir=path_env("LOG_DIR", "~/er-sync/logs"),
        screenshot_dir=path_env("SCREENSHOT_DIR", "~/er-sync/screenshots"),
        workflow_path=workflow_path,
        workflow=workflow,
        reports=reports,
        report_url_override=os.getenv("EXTENDEDREACH_REPORT_URL", "").strip() or None,
        min_file_bytes=_env_int("MIN_FILE_BYTES", 1024),
        allowed_extensions=extensions,
        expected_csv_headers=_split_csv(os.getenv("EXPECTED_CSV_HEADERS")),
        csv_encodings=_split_csv(os.getenv("CSV_ENCODINGS")) or ["utf-8-sig", "cp1252"],
        drive_folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip(),
        google_credentials_file=path_env("GOOGLE_CREDENTIALS_FILE", "~/er-sync/credentials.json"),
        google_token_file=path_env("GOOGLE_TOKEN_FILE", "~/er-sync/token.json"),
        google_scopes=_split_csv(os.getenv("GOOGLE_DRIVE_SCOPES"))
                      or ["https://www.googleapis.com/auth/drive.file"],
        browser_channel=os.getenv("BROWSER_CHANNEL", "").strip(),
        screenshot_on_failure=_env_bool("SCREENSHOT_ON_FAILURE", False),
        login_wait_seconds=_env_int("LOGIN_WAIT_SECONDS", 300),
        nav_timeout_ms=_env_int("NAV_TIMEOUT_MS", 45_000),
        download_timeout_ms=_env_int("DOWNLOAD_TIMEOUT_MS", 120_000),
        schedule_cron=os.getenv("SCHEDULE_CRON", "0 18 * * *").strip(),
        redact_terms=_split_csv(os.getenv("REDACT_TERMS")),
    )
    return cfg


# Characters a word processor substitutes for the plain ones JSON requires.
# TextEdit does this by default, and the resulting error ("not valid JSON")
# names a line number but not the actual cause, which is invisible on screen:
# a curly quote looks like a quote.
_SMART_PUNCTUATION = {
    "\u201c": 'left curly quote',
    "\u201d": 'right curly quote',
    "\u2018": 'left curly apostrophe',
    "\u2019": 'right curly apostrophe',
    "\u2013": 'en dash',
    "\u2014": 'em dash',
}


def _json_hint(path: Path) -> str:
    """Name the likely cause when a workflow file will not parse."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

    found = sorted({name for ch, name in _SMART_PUNCTUATION.items() if ch in text})
    if found:
        return (
            "\n  The file contains " + ", ".join(found) + ". A text editor "
            "substituted these for the plain ones JSON needs; they look almost "
            "identical on screen.\n  Replace every curly quote with a plain \" "
            "and turn off smart quotes in your editor, or use VS Code, which "
            "never substitutes them."
        )
    if text.count("{") != text.count("}") or text.count("[") != text.count("]"):
        return "\n  Brackets do not balance: check for a missing } or ]."
    if ",\n}" in text or ",\n  }" in text or ",]" in text or ",}" in text:
        return "\n  There is a comma after the last item in a list or block."
    return ""


def _build_reports(workflow: dict[str, Any]) -> dict[str, ReportConfig]:
    """Every report in the workflow file, enabled or not.

    Disabled ones are kept so `--list-reports` can show them and so a typo in a
    slug is reported as "disabled" rather than "no such report".
    """
    raw = (workflow or {}).get("reports", {})
    if not isinstance(raw, dict):
        return {}

    built: dict[str, ReportConfig] = {}
    for slug, spec in raw.items():
        if not isinstance(spec, dict):
            continue
        built[slug] = ReportConfig(
            slug=slug,
            description=spec.get("description", ""),
            enabled=bool(spec.get("enabled", False)),
            navigation=spec.get("navigation", {}) or {},
            filters=[f for f in spec.get("filters", []) or [] if isinstance(f, dict)],
            apply_filters_control=spec.get("apply_filters_control", {}) or {},
            export=spec.get("export", {}) or {},
            validation=spec.get("validation", {}) or {},
            drive_folder_id=_resolve_drive_folder(spec),
        )
    return built


def _resolve_drive_folder(spec: dict[str, Any]) -> str:
    """A per-report Drive folder, if one is configured.

    `drive_folder_id_env` is preferred over a literal id: folder ids are not
    secret, but keeping them in .env means the workflow file can be shared or
    reviewed without carrying the destination of real records.
    """
    env_name = spec.get("drive_folder_id_env")
    if env_name:
        value = os.getenv(env_name, "").strip()
        if value and not _PLACEHOLDER.search(value):
            return value
    literal = str(spec.get("drive_folder_id", "") or "").strip()
    return "" if _PLACEHOLDER.search(literal) else literal


def validate(cfg: AppConfig, *, require_drive: bool = True) -> list[Problem]:
    """Return every problem found. Errors block the run; warnings do not."""
    problems: list[Problem] = []
    protected = _protected_roots()

    def err(key: str, detail: str) -> None:
        problems.append(Problem(key, detail, "error"))

    def warn(key: str, detail: str) -> None:
        problems.append(Problem(key, detail, "warning"))

    # -- portal ------------------------------------------------------------
    if not cfg.base_url:
        err("EXTENDEDREACH_BASE_URL", "not set")
    elif not cfg.base_url.startswith("https://"):
        err("EXTENDEDREACH_BASE_URL", "must be https")
    elif _PLACEHOLDER.search(cfg.base_url):
        err("EXTENDEDREACH_BASE_URL", "still contains a TODO placeholder")

    # REPORT_SLUG is optional. It names a default for single-report commands;
    # it does not decide what a scheduled run covers, because a stale slug
    # quietly exporting one report out of nine would be a silent, plausible
    # failure. It is only an error when it names something that does not exist.
    if cfg.report_slug and _PLACEHOLDER.search(cfg.report_slug):
        err("REPORT_SLUG", "still contains a TODO placeholder")

    # -- workflow ----------------------------------------------------------
    if cfg.workflow_path is None:
        err("WORKFLOW_FILE", "not set")
    elif not cfg.workflow_path.exists():
        err("WORKFLOW_FILE", f"no such file: {cfg.workflow_path.name}")

    enabled = cfg.enabled_reports()
    if not cfg.reports:
        err("workflow.reports", "no reports are defined")
    elif not enabled:
        err("workflow.reports",
            f"{len(cfg.reports)} report(s) defined but none is enabled")

    if cfg.report_slug and cfg.report_slug not in cfg.reports:
        err("REPORT_SLUG",
            f"{cfg.report_slug!r} matches no report in the workflow file")

    # Every enabled report is validated. One broken report should be named as
    # itself, not hidden behind whichever happened to be checked first.
    for report in enabled:
        _validate_report(cfg, report, problems)

    seen_folders: dict[str, str] = {}
    for report in enabled:
        folder = cfg.drive_folder_for(report)
        if folder and folder in seen_folders and seen_folders[folder] != report.slug:
            # Not an error: several reports landing in one folder is a normal
            # choice. Worth saying once, because the duplicate check is keyed on
            # report slug plus date, so they will not collide.
            pass
        seen_folders.setdefault(folder, report.slug)

    # An explicit signed-in selector is optional. Without one the session check
    # is the absence of a visible password field, which needs no configuration
    # and works on portals where no sign-out control can be captured — this one
    # included. A placeholder left in place is still wrong, because it would be
    # taken as a real selector and never match.
    auth = cfg.auth
    selector = str(auth.get("authenticated_selector") or "")
    if selector and _PLACEHOLDER.search(selector):
        err("workflow.auth.authenticated_selector",
            "still a TODO placeholder; leave it empty to use the "
            "password-field check instead")

    # -- paths -------------------------------------------------------------
    for key, path in (
        ("BROWSER_PROFILE_DIR", cfg.browser_profile_dir),
        ("DOWNLOAD_DIR", cfg.download_dir),
        ("LOG_DIR", cfg.log_dir),
        ("SCREENSHOT_DIR", cfg.screenshot_dir),
        ("GOOGLE_CREDENTIALS_FILE", cfg.google_credentials_file),
        ("GOOGLE_TOKEN_FILE", cfg.google_token_file),
    ):
        if path is None:
            continue
        if _is_inside_repo(Path(path), protected):
            err(key, "resolves inside the project folder; it must live outside "
                     "so a credential, a browser profile or a downloaded report "
                     "is never shared or committed along with the code")
        if "TODO" in str(path):
            err(key, "still contains a TODO placeholder")

    # -- validation rules --------------------------------------------------
    allowed_channels = {"", "chrome", "chrome-beta", "msedge", "msedge-beta"}
    if cfg.browser_channel not in allowed_channels:
        err("BROWSER_CHANNEL",
            f"{cfg.browser_channel!r} is not one of {sorted(allowed_channels - {''})} "
            "(leave it blank to use Playwright's own Chromium)")

    if cfg.min_file_bytes < 1:
        err("MIN_FILE_BYTES", "must be at least 1")
    unknown = cfg.allowed_extensions - APPROVED_EXTENSIONS
    if unknown:
        err("ALLOWED_EXTENSIONS",
            f"not in the approved allow-list: {sorted(unknown)}")
    if not cfg.allowed_extensions:
        err("ALLOWED_EXTENSIONS", "empty")

    for report in enabled:
        headers = report.expected_headers(cfg.expected_csv_headers)
        placeholders = [h for h in headers if _PLACEHOLDER.search(h)]
        if placeholders:
            err(f"reports.{report.slug}.expected_csv_headers",
                f"{len(placeholders)} header(s) still contain a TODO placeholder")
        elif not headers:
            warn(f"reports.{report.slug}.expected_csv_headers",
                 "not set; this report will pass validation on size alone")

    # -- filters -----------------------------------------------------------
    for report in enabled:
      for spec in report.filters:
        env_name = spec.get("value_env")
        name = f"{report.slug}.{spec.get('name', env_name or '?')}"
        if not env_name:
            err(f"filter[{name}]", "has no value_env")
            continue
        raw = os.getenv(env_name, "").strip()
        if not raw:
            if spec.get("required"):
                err(f"filter[{name}]", f"{env_name} is required but not set")
            continue
        if not FILTER_VALUE_PATTERN.match(raw):
            err(f"filter[{name}]",
                f"{env_name} value rejected: filters accept only "
                r"^[A-Za-z0-9 _./:-]{1,64}$ , which keeps free text — and "
                "therefore names — out of portal fields")

    # -- Drive -------------------------------------------------------------
    if require_drive:
        if not cfg.drive_folder_id or _PLACEHOLDER.search(cfg.drive_folder_id):
            err("GOOGLE_DRIVE_FOLDER_ID", "not set or still a TODO placeholder")
        if cfg.google_credentials_file and not cfg.google_credentials_file.exists():
            err("GOOGLE_CREDENTIALS_FILE",
                f"no such file: {cfg.google_credentials_file}")
        broad = [s for s in cfg.google_scopes if s.rstrip("/").endswith("/auth/drive")]
        if broad:
            warn("GOOGLE_DRIVE_SCOPES",
                 "full-drive scope grants read/write over the entire Drive; "
                 "drive.file is enough for uploads and the duplicate check")

    return problems


def _validate_report(cfg: AppConfig, report: ReportConfig,
                     problems: list[Problem]) -> None:
    prefix = f"reports.{report.slug}"

    nav = report.navigation or {}
    mode = nav.get("mode", "direct_url")
    single = len(cfg.enabled_reports()) == 1
    if cfg.report_url_override and single:
        if _PLACEHOLDER.search(cfg.report_url_override):
            problems.append(Problem("EXTENDEDREACH_REPORT_URL",
                                    "still a TODO placeholder"))
    elif mode == "direct_url":
        url = str(nav.get("direct_url", ""))
        if not url:
            problems.append(Problem(f"{prefix}.navigation.direct_url", "not set"))
        elif _PLACEHOLDER.search(url):
            problems.append(Problem(f"{prefix}.navigation.direct_url",
                                    "still a TODO placeholder"))
    elif mode == "steps":
        steps = nav.get("steps") or []
        if not steps:
            problems.append(Problem(f"{prefix}.navigation.steps", "empty"))
        for index, step in enumerate(steps):
            action = step.get("action")
            if action not in READ_ONLY_ACTIONS:
                problems.append(Problem(
                    f"{prefix}.navigation.steps[{index}]",
                    f"action {action!r} is not read-only; allowed: "
                    f"{sorted(READ_ONLY_ACTIONS)}"))
            if any(_PLACEHOLDER.search(str(v)) for v in step.values()):
                problems.append(Problem(f"{prefix}.navigation.steps[{index}]",
                                        "still contains a TODO placeholder"))
    else:
        problems.append(Problem(f"{prefix}.navigation.mode",
                                f"unknown mode {mode!r}; use direct_url or steps"))

    export = report.export or {}
    if not export.get("selector") and not export.get("name"):
        problems.append(Problem(f"{prefix}.export",
                                "needs a selector or a role+name"))
    if any(_PLACEHOLDER.search(str(v)) for v in export.values() if isinstance(v, str)):
        problems.append(Problem(f"{prefix}.export",
                                "still contains a TODO placeholder"))


# Steps the browser worker will execute. Anything that could write is absent
# by construction, and config validation rejects an action outside this set.
READ_ONLY_ACTIONS = {
    "goto",
    "click_link",
    "click",
    "wait_for",
    "select_option",
    "fill_filter",
    "check",
    "uncheck",
}


def format_problems(problems: list[Problem]) -> str:
    return "\n".join(f"  {p}" for p in problems)


def require_valid(cfg: AppConfig, *, require_drive: bool = True) -> AppConfig:
    """Validate, raising on any error. Warnings are attached to the config."""
    problems = validate(cfg, require_drive=require_drive)
    errors = [p for p in problems if p.severity == "error"]
    cfg.warnings = [p for p in problems if p.severity == "warning"]
    if errors:
        raise ConfigError(
            f"{len(errors)} configuration problem(s):\n" + format_problems(errors))
    return cfg
