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
        reports=config_module._build_reports(workflow),
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
    cfg = _config(tmp_path, base_url="", drive_folder_id="",
                  report_slug="not_a_report")
    with pytest.raises(ConfigError) as excinfo:
        require_valid(cfg)
    message = str(excinfo.value)
    assert "EXTENDEDREACH_BASE_URL" in message
    assert "REPORT_SLUG" in message
    assert "GOOGLE_DRIVE_FOLDER_ID" in message


def test_an_unset_report_slug_is_not_an_error(tmp_path):
    """It names a default for single-report commands; it does not decide what a
    scheduled run covers."""
    cfg = _config(tmp_path, report_slug="")
    assert _errors(cfg) == []


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
    assert "reports.pastdue_case.expected_csv_headers" in _keys(_errors(cfg))


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

def _multi(tmp_path, count=3, **overrides):
    workflow = json.loads(json.dumps(WORKFLOW))
    template = workflow["reports"]["pastdue_case"]
    for index in range(1, count):
        clone = json.loads(json.dumps(template))
        clone["navigation"]["direct_url"] = f"/reports/view?id=R{index}"
        workflow["reports"][f"report_{index}"] = clone
    return _config(tmp_path, workflow_json=workflow, **overrides)


def test_many_enabled_reports_are_allowed(tmp_path):
    """Nine reports is the actual requirement; more than one is not an error."""
    cfg = _multi(tmp_path, count=9)
    assert _errors(cfg) == []
    assert len(cfg.enabled_reports()) == 9


def test_every_enabled_report_runs_by_default(tmp_path):
    cfg = _multi(tmp_path, count=9)
    assert len(cfg.selected_reports()) == 9


def test_a_stale_report_slug_does_not_narrow_a_run(tmp_path):
    """REPORT_SLUG naming one report must not quietly export one of nine."""
    cfg = _multi(tmp_path, count=9, report_slug="pastdue_case")
    assert len(cfg.selected_reports()) == 9


def test_one_report_can_be_selected_explicitly(tmp_path):
    cfg = _multi(tmp_path, count=9)
    chosen = cfg.selected_reports("report_3")
    assert [r.slug for r in chosen] == ["report_3"]


def test_selecting_an_unknown_report_selects_nothing(tmp_path):
    assert _multi(tmp_path).selected_reports("nope") == []


def test_disabled_reports_are_kept_but_not_run(tmp_path):
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["retired"] = json.loads(
        json.dumps(workflow["reports"]["pastdue_case"]))
    workflow["reports"]["retired"]["enabled"] = False
    cfg = _config(tmp_path, workflow_json=workflow)
    assert "retired" in cfg.reports
    assert [r.slug for r in cfg.enabled_reports()] == ["pastdue_case"]


def test_no_enabled_reports_is_an_error(tmp_path):
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["enabled"] = False
    cfg = _config(tmp_path, workflow_json=workflow)
    assert "workflow.reports" in _keys(_errors(cfg))


def test_a_slug_matching_no_report_is_refused(tmp_path):
    cfg = _config(tmp_path, report_slug="not_a_report")
    assert "REPORT_SLUG" in _keys(_errors(cfg))


def test_a_broken_report_is_named_by_its_own_slug(tmp_path):
    """With nine reports, "the export selector is missing" is useless unless it
    says which report."""
    workflow = json.loads(json.dumps(WORKFLOW))
    clone = json.loads(json.dumps(workflow["reports"]["pastdue_case"]))
    clone["export"] = {}
    workflow["reports"]["broken_one"] = clone
    cfg = _config(tmp_path, workflow_json=workflow)
    keys = _keys(_errors(cfg))
    assert any("broken_one" in k for k in keys)
    assert not any("pastdue_case" in k for k in keys)


# -- per-report validation rules -------------------------------------------

def test_each_report_carries_its_own_expected_columns(tmp_path):
    """Nine reports have nine different column sets; one global list would be
    wrong for eight of them."""
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["validation"] = {
        "expected_csv_headers": ["Case #", "Due Date"]}
    other = json.loads(json.dumps(workflow["reports"]["pastdue_case"]))
    other["validation"] = {"expected_csv_headers": ["Home", "Beds"]}
    workflow["reports"]["openbeds"] = other
    cfg = _config(tmp_path, workflow_json=workflow)
    assert cfg.reports["pastdue_case"].expected_headers([]) == ["Case #", "Due Date"]
    assert cfg.reports["openbeds"].expected_headers([]) == ["Home", "Beds"]


def test_a_report_without_columns_falls_back_to_the_global_list(tmp_path):
    cfg = _config(tmp_path)
    assert cfg.reports["pastdue_case"].expected_headers(["A", "B"]) == ["A", "B"]


def test_an_explicit_empty_column_list_means_do_not_check(tmp_path):
    """Distinct from the key being absent, which falls back."""
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["validation"] = {"expected_csv_headers": []}
    cfg = _config(tmp_path, workflow_json=workflow)
    assert cfg.reports["pastdue_case"].expected_headers(["A"]) == []


def test_a_placeholder_column_blocks_only_its_own_report(tmp_path):
    workflow = json.loads(json.dumps(WORKFLOW))
    clone = json.loads(json.dumps(workflow["reports"]["pastdue_case"]))
    clone["validation"] = {"expected_csv_headers": ["TODO_COLUMN"]}
    workflow["reports"]["unfinished"] = clone
    cfg = _config(tmp_path, workflow_json=workflow)
    assert "reports.unfinished.expected_csv_headers" in _keys(_errors(cfg))


def test_a_report_can_override_the_minimum_file_size(tmp_path):
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["validation"] = {"min_file_bytes": 50_000}
    cfg = _config(tmp_path, workflow_json=workflow)
    assert cfg.reports["pastdue_case"].min_bytes(1024) == 50_000
    assert cfg.reports["pastdue_case"].min_bytes(1024) != 1024


def test_a_nonsense_minimum_size_falls_back_rather_than_crashing(tmp_path):
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["validation"] = {"min_file_bytes": "big"}
    cfg = _config(tmp_path, workflow_json=workflow)
    assert cfg.reports["pastdue_case"].min_bytes(1024) == 1024


# -- per-report Drive folders ----------------------------------------------

def test_reports_share_the_global_drive_folder_by_default(tmp_path):
    cfg = _multi(tmp_path, count=3)
    folders = {cfg.drive_folder_for(r) for r in cfg.enabled_reports()}
    assert folders == {cfg.drive_folder_id}


def test_a_report_can_be_sent_to_its_own_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIVE_FOLDER_BEDS", "1BedsFolderIdAbc")
    workflow = json.loads(json.dumps(WORKFLOW))
    clone = json.loads(json.dumps(workflow["reports"]["pastdue_case"]))
    clone["drive_folder_id_env"] = "DRIVE_FOLDER_BEDS"
    workflow["reports"]["openbeds"] = clone
    cfg = _config(tmp_path, workflow_json=workflow)
    assert cfg.drive_folder_for(cfg.reports["openbeds"]) == "1BedsFolderIdAbc"
    assert cfg.drive_folder_for(cfg.reports["pastdue_case"]) == cfg.drive_folder_id


def test_an_unset_per_report_folder_falls_back_to_the_global_one(tmp_path, monkeypatch):
    monkeypatch.delenv("DRIVE_FOLDER_BEDS", raising=False)
    workflow = json.loads(json.dumps(WORKFLOW))
    workflow["reports"]["pastdue_case"]["drive_folder_id_env"] = "DRIVE_FOLDER_BEDS"
    cfg = _config(tmp_path, workflow_json=workflow)
    assert cfg.drive_folder_for(cfg.reports["pastdue_case"]) == cfg.drive_folder_id


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
    assert any("filter[pastdue_case.worker]" in p.key for p in _errors(cfg))


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
    assert any("filter[pastdue_case.program]" in p.key for p in _errors(cfg))


# -- warnings ---------------------------------------------------------------

def test_missing_csv_headers_warn_rather_than_block(tmp_path):
    cfg = _config(tmp_path, expected_csv_headers=[])
    problems = validate(cfg)
    warnings = {p.key for p in problems if p.severity == "warning"}
    assert "reports.pastdue_case.expected_csv_headers" in warnings
    assert _errors(cfg) == []


def test_problem_formatting_marks_errors_and_warnings_distinctly():
    assert str(Problem("K", "d", "error")).startswith("ERROR")
    assert str(Problem("K", "d", "warning")).startswith("WARN")


# -- unparseable workflow files --------------------------------------------

def test_curly_quotes_are_named_as_the_cause(tmp_path, monkeypatch):
    """A text editor substituting curly quotes is the likeliest way a
    non-developer breaks this file, and the damage is invisible on screen:
    a curly quote looks like a quote."""
    path = tmp_path / "workflow.json"
    path.write_text('{“reports”: {}}', encoding="utf-8")
    monkeypatch.setenv("WORKFLOW_FILE", str(path))
    with pytest.raises(ConfigError) as excinfo:
        config_module.load()
    message = str(excinfo.value)
    assert "curly quote" in message
    assert "smart quotes" in message


def test_unbalanced_brackets_are_named(tmp_path, monkeypatch):
    path = tmp_path / "workflow.json"
    path.write_text('{"reports": {"a": {}}', encoding="utf-8")
    monkeypatch.setenv("WORKFLOW_FILE", str(path))
    with pytest.raises(ConfigError) as excinfo:
        config_module.load()
    assert "Brackets do not balance" in str(excinfo.value)


def test_a_trailing_comma_is_named(tmp_path, monkeypatch):
    path = tmp_path / "workflow.json"
    path.write_text('{"reports": {"a": 1,}}', encoding="utf-8")
    monkeypatch.setenv("WORKFLOW_FILE", str(path))
    with pytest.raises(ConfigError) as excinfo:
        config_module.load()
    assert "comma after the last item" in str(excinfo.value)


def test_the_error_always_gives_line_and_column(tmp_path, monkeypatch):
    path = tmp_path / "workflow.json"
    path.write_text('{\n  "reports": nonsense\n}', encoding="utf-8")
    monkeypatch.setenv("WORKFLOW_FILE", str(path))
    with pytest.raises(ConfigError) as excinfo:
        config_module.load()
    assert "line 2" in str(excinfo.value)


# -- the protected-paths guard must not depend on git -----------------------

def test_the_project_folder_is_protected_without_a_git_directory(tmp_path, monkeypatch):
    """The guard used to look only for a .git directory, so it silently did
    nothing for anyone who downloaded the project as a zip — the people least
    likely to notice a browser profile full of session cookies sitting next to
    the code."""
    monkeypatch.setattr(config_module, "_repo_root", lambda _start: None)
    inside = config_module._project_root() / "downloads"
    assert config_module._is_inside_repo(
        inside, config_module._protected_roots()) is True


def test_a_path_outside_the_project_is_allowed_without_git(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_repo_root", lambda _start: None)
    assert config_module._is_inside_repo(
        tmp_path / "er-sync", config_module._protected_roots()) is False


def test_every_sensitive_path_is_still_refused_without_git(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_repo_root", lambda _start: None)
    inside = config_module._project_root() / "should_not_exist"
    for field, key in (("browser_profile_dir", "BROWSER_PROFILE_DIR"),
                       ("download_dir", "DOWNLOAD_DIR"),
                       ("log_dir", "LOG_DIR"),
                       ("google_token_file", "GOOGLE_TOKEN_FILE")):
        cfg = _config(tmp_path, **{field: inside})
        assert key in _keys(_errors(cfg)), f"{key} was allowed inside the project"


def test_the_git_root_is_still_protected_when_present(tmp_path):
    """A project nested inside a larger repository stays protected up to the
    repository boundary."""
    roots = config_module._protected_roots()
    assert config_module._project_root() in roots
