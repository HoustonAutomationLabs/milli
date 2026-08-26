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


def _repo_root(start: Path) -> Optional[Path]:
    """The git repository this file sits in, if any."""
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _is_inside_repo(path: Path, repo: Optional[Path]) -> bool:
    if repo is None:
        return False
    try:
        path.resolve().relative_to(repo.resolve())
        return True
    except ValueError:
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
    """One report. The POC implements exactly one; the shape is a map so more
    can be added without restructuring."""

    slug: str
    description: str = ""
    navigation: dict[str, Any] = field(default_factory=dict)
    filters: list[dict[str, Any]] = field(default_factory=list)
    apply_filters_control: dict[str, Any] = field(default_factory=dict)
    export: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)


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
    report: Optional[ReportConfig] = None
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
    def auth(self) -> dict[str, Any]:
        return self.workflow.get("auth", {}) if self.workflow else {}

    @property
    def safety(self) -> dict[str, Any]:
        return self.workflow.get("safety", {}) if self.workflow else {}

    def filter_values(self) -> dict[str, str]:
        """Resolved filter values, keyed by filter name. Values that fail the
        pattern are omitted here and reported by validate()."""
        resolved: dict[str, str] = {}
        for spec in (self.report.filters if self.report else []):
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
                    f"{workflow_path.name} is not valid JSON (line {exc.lineno})"
                ) from None

    slug = os.getenv("REPORT_SLUG", "").strip()
    report = _select_report(workflow, slug)

    extensions = {e.lower().lstrip(".") for e in
                  _split_csv(os.getenv("ALLOWED_EXTENSIONS")) } or set(APPROVED_EXTENSIONS)

    cfg = AppConfig(
        base_url=os.getenv("EXTENDEDREACH_BASE_URL", "").strip(),
        report_slug=slug or (report.slug if report else ""),
        browser_profile_dir=path_env("BROWSER_PROFILE_DIR", "~/er-sync/profile"),
        download_dir=path_env("DOWNLOAD_DIR", "~/er-sync/downloads"),
        log_dir=path_env("LOG_DIR", "~/er-sync/logs"),
        screenshot_dir=path_env("SCREENSHOT_DIR", "~/er-sync/screenshots"),
        workflow_path=workflow_path,
        workflow=workflow,
        report=report,
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
        screenshot_on_failure=_env_bool("SCREENSHOT_ON_FAILURE", False),
        login_wait_seconds=_env_int("LOGIN_WAIT_SECONDS", 300),
        nav_timeout_ms=_env_int("NAV_TIMEOUT_MS", 45_000),
        download_timeout_ms=_env_int("DOWNLOAD_TIMEOUT_MS", 120_000),
        schedule_cron=os.getenv("SCHEDULE_CRON", "0 18 * * *").strip(),
        redact_terms=_split_csv(os.getenv("REDACT_TERMS")),
    )
    return cfg


def _select_report(workflow: dict[str, Any], slug: str) -> Optional[ReportConfig]:
    reports = (workflow or {}).get("reports", {})
    if not isinstance(reports, dict) or not reports:
        return None

    enabled = {k: v for k, v in reports.items()
               if isinstance(v, dict) and v.get("enabled", False)}
    chosen_key: Optional[str] = None
    if slug and slug in reports:
        chosen_key = slug
    elif len(enabled) == 1:
        chosen_key = next(iter(enabled))
    if chosen_key is None:
        return None

    spec = reports[chosen_key]
    return ReportConfig(
        slug=chosen_key,
        description=spec.get("description", ""),
        navigation=spec.get("navigation", {}) or {},
        filters=[f for f in spec.get("filters", []) or [] if isinstance(f, dict)],
        apply_filters_control=spec.get("apply_filters_control", {}) or {},
        export=spec.get("export", {}) or {},
        validation=spec.get("validation", {}) or {},
    )


def validate(cfg: AppConfig, *, require_drive: bool = True) -> list[Problem]:
    """Return every problem found. Errors block the run; warnings do not."""
    problems: list[Problem] = []
    repo = _repo_root(Path(__file__).resolve())

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

    if not cfg.report_slug:
        err("REPORT_SLUG", "not set")
    elif _PLACEHOLDER.search(cfg.report_slug):
        err("REPORT_SLUG", "still contains a TODO placeholder")

    # -- workflow ----------------------------------------------------------
    if cfg.workflow_path is None:
        err("WORKFLOW_FILE", "not set")
    elif not cfg.workflow_path.exists():
        err("WORKFLOW_FILE", f"no such file: {cfg.workflow_path.name}")

    reports = (cfg.workflow or {}).get("reports", {})
    enabled = [k for k, v in reports.items()
               if isinstance(v, dict) and v.get("enabled", False)]
    if len(enabled) > 1:
        err("workflow.reports",
            f"{len(enabled)} reports enabled; this POC supports exactly one")

    if cfg.report is None:
        if reports:
            err("workflow.reports", f"no report matches REPORT_SLUG={cfg.report_slug!r}")
    else:
        _validate_report(cfg, problems)

    auth = cfg.auth
    if not auth.get("authenticated_selector"):
        err("workflow.auth.authenticated_selector", "not set")
    elif _PLACEHOLDER.search(str(auth.get("authenticated_selector"))):
        err("workflow.auth.authenticated_selector", "still a TODO placeholder")
    if not auth.get("login_form_selector"):
        warn("workflow.auth.login_form_selector",
             "not set; the tool can still detect a signed-in session but "
             "cannot positively identify the login page")

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
        if _is_inside_repo(Path(path), repo):
            err(key, "resolves inside the git repository; it must live outside "
                     "so a credential, a browser profile or a PHI download can "
                     "never be committed")
        if "TODO" in str(path):
            err(key, "still contains a TODO placeholder")

    # -- validation rules --------------------------------------------------
    if cfg.min_file_bytes < 1:
        err("MIN_FILE_BYTES", "must be at least 1")
    unknown = cfg.allowed_extensions - APPROVED_EXTENSIONS
    if unknown:
        err("ALLOWED_EXTENSIONS",
            f"not in the approved allow-list: {sorted(unknown)}")
    if not cfg.allowed_extensions:
        err("ALLOWED_EXTENSIONS", "empty")

    wants_csv = "csv" in cfg.allowed_extensions
    placeholders = [h for h in cfg.expected_csv_headers if _PLACEHOLDER.search(h)]
    if wants_csv and not cfg.expected_csv_headers:
        warn("EXPECTED_CSV_HEADERS",
             "not set; a CSV export will pass validation on size alone")
    if placeholders:
        err("EXPECTED_CSV_HEADERS",
            f"{len(placeholders)} header(s) still contain a TODO placeholder")

    # -- filters -----------------------------------------------------------
    for spec in (cfg.report.filters if cfg.report else []):
        env_name = spec.get("value_env")
        name = spec.get("name", env_name or "?")
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


def _validate_report(cfg: AppConfig, problems: list[Problem]) -> None:
    report = cfg.report
    assert report is not None
    prefix = f"reports.{report.slug}"

    nav = report.navigation or {}
    mode = nav.get("mode", "direct_url")
    if cfg.report_url_override:
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
