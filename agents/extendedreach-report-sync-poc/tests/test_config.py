"""Configuration validation.

The two rules with teeth here:

* Nothing that holds a credential, a browser session or a downloaded report
  may resolve inside the git repository.
* A filter value that is not obviously non-sensitive is refused, so this tool
  cannot type a person's name into a portal search box.
"""

import json
from pathlib import Path

import pytest

from src import config as config_module
from src.config import (
    FILTER_VALUE_PATTERN,
    AppConfig,
    ConfigError,
    Problem,
    READ_ONLY_ACTIONS,
    require_valid,
    validate,
)

WORKFLOW = {
    "version": 1,
    "auth": {
        "authenticated_selector": "#account-menu",
        "login_form_selector": "#login",
        "mfa_selectors": ["#mfa-code"],
        "captcha_selectors": [],
    },
    "safety": {
        "url_denylist_substrings": ["delete", "edit"],
        "screenshot_safe_url_substrings": ["/login"],
    },
    "reports": {
        "pastdue_case": {
            "enabled": True,
            "description": "Past due case tasks",
            "navigation": {"mode": "direct_url", "direct_url": "/reports/view?id=X"},
            "filters": [],
            "export": {"selector": "#export-excel"},
            "validation": {"expected_extension": "csv"},
        }
    },
}


def _write_workflow(tmp_path: Path, workflow=None) -> Path:
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(workflow or WORKFLOW), encoding="utf-8")
    return path


def _config(tmp_path: Path, **overrides) -> AppConfig:
    """A configuration that is valid by default, so each test can break one
    thing and see only that failure."""
    outside = tmp_path / "outside"
    creds = outside / "credentials.json"
    creds.parent.mkdir(parents=True, exist_ok=True)
    creds.write_text("{}", encoding="utf-8")

    workflow_path = _write_workflow(tmp_path, overrides.pop("workflow_json", None))
    workflow = json.loads(workflow_path.read_text())

    defaults = dict(
        base_url="https://portal.example.com",
        report_slug="pastdue_case",
        browser_profile_dir=outside / "profile",
        download_dir=outside / "downloads",
        log_dir=outside / "logs",
        screenshot_dir=outside / "screenshots",
        workflow_path=workflow_path,
        workflow=workflow,
        report=config_module._select_report(workflow, "pastdue_case"),
        expected_csv_headers=["Case #", "Status"],
        drive_folder_id="1AbCdEfGhIjKlMnOpQrStUvWxYz",
        google_credentials_file=creds,
        google_token_file=outside / "token.json",
    )
    defaults.update(overrides)
    return AppConfig(**defaults)


def _errors(cfg, **kwargs):
    return [p for p in validate(cfg, **kwargs) if p.severity == "error"]


def _keys(problems):
    return {p.key for p in problems}


# -- the baseline -----------------------------------------------------------

def test_a_fully_configured_setup_validates_clean(tmp_path):
    assert _errors(_config(tmp_path)) == []


def test_require_valid_returns_the_config_when_it_is_valid(tmp_path):
    cfg = _config(tmp_path)
    assert require_valid(cfg) is cfg


def test_require_valid_raises_and_lists_every_problem_at_once(tmp_path):
    cfg = _config(tmp_path, base_url="", report_slug="", drive_folder_id="")
    with pytest.raises(ConfigError) as excinfo:
        require_valid(cfg)
    message = str(excinfo.value)
    assert "EXTENDEDREACH_BASE_URL" in message
    assert "REPORT_SLUG" in message
    assert "GOOGLE_DRIVE_FOLDER_ID" in message


# -- paths must live outside the repository ---------------------------------

@pytest.mark.parametrize("key,field", [
    ("BROWSER_PROFILE_DIR", "browser_profile_dir"),
    ("DOWNLOAD_DIR", "download_dir"),
    ("LOG_DIR", "log_dir"),
    ("SCREENSHOT_DIR", "screenshot_dir"),
    ("GOOGLE_TOKEN_FILE", "google_token_file"),
])
def test_a_path_inside_the_repository_is_an_error(tmp_path, key, field):
    """A browser profile, a token or a downloaded report inside the repo is one
    `git add -A` away from being published."""
    inside = Path(config_module.__file__).resolve().parent.parent / "should_not_exist"
    cfg = _config(tmp_path, **{field: inside})
    assert key in _keys(_errors(cfg))


def test_paths_outside_the_repository_are_accepted(tmp_path):
    assert "DOWNLOAD_DIR" not in _keys(_errors(_config(tmp_path)))


# -- placeholders -----------------------------------------------------------

def test_an_unfilled_todo_placeholder_blocks_the_run(tmp_path):
    cfg = _config(tmp_path, base_url="https://TODO.example.com")
    assert "EXTENDEDREACH_BASE_URL" in _keys(_errors(cfg))


def test_a_todo_drive_folder_blocks_the_run(tmp_path):
    cfg = _config(tmp_path, drive_folder_id="TODO_DRIVE_FOLDER_ID")
    assert "GOOGLE_DRIVE_FOLDER_ID" in _keys(_errors(cfg))


def test_todo_csv_headers_block_the_run(tmp_path):
    cfg = _config(tmp_path, expected_csv_headers=["TODO_COLUMN_ONE"])
    assert "EXPECTED_CSV_HEADERS" in _keys(_errors(cfg))


def test_a_placeholder_export_selector_blocks_the_run(tmp_path):
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["export"] = {"selector": "TODO_SELECTOR"}
    cfg = _config(tmp_path, workflow_json=workflow)
    assert any("export" in key for key in _keys(_errors(cfg)))


# -- transport and scope ----------------------------------------------------

def test_a_non_https_portal_url_is_refused(tmp_path):
    cfg = _config(tmp_path, base_url="http://portal.example.com")
    assert "EXTENDEDREACH_BASE_URL" in _keys(_errors(cfg))


def test_drive_checks_are_skipped_for_a_dry_run(tmp_path):
    cfg = _config(tmp_path, drive_folder_id="")
    assert _errors(cfg, require_drive=False) == []
    assert "GOOGLE_DRIVE_FOLDER_ID" in _keys(_errors(cfg, require_drive=True))


def test_the_full_drive_scope_warns_but_does_not_block(tmp_path):
    cfg = _config(tmp_path,
                  google_scopes=["https://www.googleapis.com/auth/drive"])
    problems = validate(cfg)
    assert "GOOGLE_DRIVE_SCOPES" in {p.key for p in problems if p.severity == "warning"}
    assert "GOOGLE_DRIVE_SCOPES" not in _keys(_errors(cfg))


# -- extensions -------------------------------------------------------------

def test_an_extension_outside_the_approved_list_is_refused(tmp_path):
    cfg = _config(tmp_path, allowed_extensions={"csv", "exe"})
    assert "ALLOWED_EXTENSIONS" in _keys(_errors(cfg))


def test_an_empty_extension_list_is_refused(tmp_path):
    cfg = _config(tmp_path, allowed_extensions=set())
    assert "ALLOWED_EXTENSIONS" in _keys(_errors(cfg))


# -- one report only --------------------------------------------------------

def test_more_than_one_enabled_report_is_refused(tmp_path):
    """The POC implements exactly one report; two enabled is a misconfiguration
    rather than a silent choice of whichever came first."""
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["second"] = json.loads(
        json.dumps(workflow["reports"]["pastdue_case"]))
    cfg = _config(tmp_path, workflow_json=workflow)
    assert "workflow.reports" in _keys(_errors(cfg))


def test_a_slug_matching_no_report_is_refused(tmp_path):
    cfg = _config(tmp_path, report_slug="not_a_report", report=None)
    assert "workflow.reports" in _keys(_errors(cfg))


# -- read-only guarantee ----------------------------------------------------

def test_a_write_action_in_a_workflow_step_is_refused(tmp_path):
    """The workflow file is operator-editable, so a step that could modify a
    record must be refused at configuration time, not at click time."""
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["navigation"] = {
        "mode": "steps",
        "steps": [{"action": "submit_form", "selector": "#approve"}],
    }
    cfg = _config(tmp_path, workflow_json=workflow)
    problems = _errors(cfg)
    assert any("steps[0]" in p.key for p in problems)


def test_the_read_only_action_set_contains_no_write_verbs():
    forbidden = {"submit", "submit_form", "delete", "approve", "reject",
                 "save", "create", "update", "post"}
    assert READ_ONLY_ACTIONS & forbidden == set()


# -- filter values ----------------------------------------------------------

@pytest.mark.parametrize("value", [
    "Last 30 Days", "Foster Care", "2026-01-01", "A/B", "In Process", "12:00",
])
def test_predefined_non_sensitive_filter_values_are_accepted(value):
    assert FILTER_VALUE_PATTERN.match(value)


@pytest.mark.parametrize("value", [
    "O'Brien",                      # an apostrophe: almost always a surname
    "Smith, Jane",                  # a comma-separated name
    "child's medication list",      # free text
    "x" * 65,                       # unbounded input
    "",                             # empty
    "<script>",                     # markup
    "Jane\nDoe",                    # newline injection
])
def test_free_text_and_name_shaped_filter_values_are_refused(value):
    assert not FILTER_VALUE_PATTERN.match(value)


def test_a_rejected_filter_value_blocks_the_run(tmp_path, monkeypatch):
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["filters"] = [
        {"name": "worker", "type": "fill_filter", "selector": "#q",
         "value_env": "REPORT_FILTER_WORKER"}
    ]
    monkeypatch.setenv("REPORT_FILTER_WORKER", "Smith, Jane")
    cfg = _config(tmp_path, workflow_json=workflow)
    assert any("filter[worker]" in p.key for p in _errors(cfg))


def test_a_rejected_filter_value_is_never_resolved_for_use(tmp_path, monkeypatch):
    """Rejected values must not reach filter_values(), which is what the
    browser worker types into the page."""
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["filters"] = [
        {"name": "worker", "type": "fill_filter", "selector": "#q",
         "value_env": "REPORT_FILTER_WORKER"}
    ]
    monkeypatch.setenv("REPORT_FILTER_WORKER", "O'Brien, Mary")
    cfg = _config(tmp_path, workflow_json=workflow)
    assert "worker" not in cfg.filter_values()


def test_a_required_filter_with_no_value_blocks_the_run(tmp_path, monkeypatch):
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["filters"] = [
        {"name": "program", "type": "select_option", "selector": "#p",
         "value_env": "REPORT_FILTER_PROGRAM", "required": True}
    ]
    monkeypatch.delenv("REPORT_FILTER_PROGRAM", raising=False)
    cfg = _config(tmp_path, workflow_json=workflow)
    assert any("filter[program]" in p.key for p in _errors(cfg))


# -- warnings ---------------------------------------------------------------

def test_missing_csv_headers_warn_rather_than_block(tmp_path):
    cfg = _config(tmp_path, expected_csv_headers=[])
    problems = validate(cfg)
    assert "EXPECTED_CSV_HEADERS" in {p.key for p in problems if p.severity == "warning"}
    assert "EXPECTED_CSV_HEADERS" not in _keys(_errors(cfg))


def test_problem_formatting_marks_errors_and_warnings_distinctly():
    assert str(Problem("K", "d", "error")).startswith("ERROR")
    assert str(Problem("K", "d", "warning")).startswith("WARN")
