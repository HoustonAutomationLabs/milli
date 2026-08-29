"""The setup checklist.

The regression worth guarding: the example workflow file documents each
placeholder in "$comment" blocks, so those blocks contain the word TODO by
design. An earlier version checked the whole file for that word, which made
step 4 impossible to complete no matter what the operator filled in.
"""

import json

import pytest

from src import doctor
from src.doctor import DONE, SKIP, TODO


def _write(tmp_path, data):
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "workflow.json").write_text(
        json.dumps(data), encoding="utf-8")
    return tmp_path


FILLED = {
    "auth": {"authenticated_selector": "#account-menu"},
    "reports": {"pastdue_case": {"enabled": True,
                                 "export": {"selector": "#export"}}},
}


def test_a_filled_workflow_counts_as_done(tmp_path):
    _write(tmp_path, FILLED)
    assert doctor._check_workflow(tmp_path).state == DONE


def test_todo_inside_a_comment_block_does_not_block_the_step(tmp_path):
    """The example's own guidance text must not count as an unfilled field."""
    with_comments = dict(FILLED)
    with_comments["$comment"] = ["Replace TODO_CSS_SELECTOR with the real one"]
    with_comments["auth"] = dict(FILLED["auth"],
                                 **{"$comment_mfa": ["TODO_ANY_SELECTOR"]})
    _write(tmp_path, with_comments)
    assert doctor._check_workflow(tmp_path).state == DONE


def test_a_real_unfilled_placeholder_does_block_the_step(tmp_path):
    unfilled = json.loads(json.dumps(FILLED))
    unfilled["auth"]["authenticated_selector"] = "TODO_CSS_SELECTOR"
    _write(tmp_path, unfilled)
    step = doctor._check_workflow(tmp_path)
    assert step.state == TODO
    assert "placeholder" in step.why


def test_a_missing_workflow_points_at_the_setup_assistant(tmp_path):
    (tmp_path / "config").mkdir()
    step = doctor._check_workflow(tmp_path)
    assert step.state == TODO
    assert "--setup-assist" in step.command


def test_an_unpromoted_draft_is_recognised(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "workflow.draft.json").write_text("{}", encoding="utf-8")
    step = doctor._check_workflow(tmp_path)
    assert step.state == TODO
    assert step.command.startswith("cp ")
    assert "workflow.draft.json" in step.command
    assert str(tmp_path) in step.command


def test_invalid_json_is_reported_rather_than_crashing(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "workflow.json").write_text("{not json", encoding="utf-8")
    assert doctor._check_workflow(tmp_path).state == TODO


# -- .env -------------------------------------------------------------------

def test_a_missing_env_file_is_the_first_thing_to_fix(tmp_path):
    """Absolute paths: the installer's window ends in the home directory, so a
    relative path there reports the file missing and reads like a failure."""
    step = doctor._check_env(tmp_path)
    assert step.state == TODO
    assert step.command.startswith("cp ")
    assert str(tmp_path) in step.command
    assert ".env.example" in step.command


def test_commented_out_todos_in_env_do_not_count(tmp_path):
    """.env.example documents optional settings in comments. Those are notes,
    not unfilled fields."""
    (tmp_path / ".env").write_text(
        "# TODO(operator): optional, see README\n"
        "# REPORT_FILTER_PROGRAM=Foster Care\n"
        "EXTENDEDREACH_BASE_URL=https://portal.example.com\n",
        encoding="utf-8")
    assert doctor._check_env(tmp_path).state == DONE


def test_a_live_todo_in_env_is_counted(tmp_path):
    (tmp_path / ".env").write_text(
        "EXTENDEDREACH_BASE_URL=https://TODO.example.com\n", encoding="utf-8")
    step = doctor._check_env(tmp_path)
    assert step.state == TODO
    assert "1 setting" in step.why


# -- run history ------------------------------------------------------------

def test_a_dry_run_success_does_not_satisfy_the_real_run_step():
    runs = [{"status": "success", "dry_run": True}]
    assert doctor._check_dry_run(runs).state == DONE
    assert doctor._check_real_run(runs).state == TODO


def test_a_real_run_needs_a_drive_file_id():
    """Success without a file id means the upload was skipped, not done."""
    runs = [{"status": "success", "dry_run": False}]
    assert doctor._check_real_run(runs).state == TODO
    runs.append({"status": "success", "dry_run": False, "drive_file_id": "1AbC"})
    assert doctor._check_real_run(runs).state == DONE


def test_failed_runs_never_count_as_done():
    runs = [{"status": "failed", "dry_run": True},
            {"status": "requires_human_login", "dry_run": False}]
    assert doctor._check_dry_run(runs).state == TODO
    assert doctor._check_real_run(runs).state == TODO


# -- platform ---------------------------------------------------------------

def test_the_schedule_step_is_not_applicable_off_macos(monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")
    assert doctor._check_schedule().state == SKIP


def test_the_schedule_step_applies_on_macos(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor.sys, "platform", "darwin")
    monkeypatch.setattr(doctor.Path, "home", staticmethod(lambda: tmp_path))
    step = doctor._check_schedule()
    assert step.state == TODO
    assert "install_schedule.sh" in step.command


# -- multi-report progress --------------------------------------------------

NINE = {f"report_{i}" for i in range(9)}


def _run(slug, status="success", dry=False, drive="1AbC"):
    return {"report_slug": slug, "status": status, "dry_run": dry,
            "drive_file_id": drive if not dry else None}


def test_partial_progress_names_what_is_left(tmp_path):
    """With nine reports, "no run has uploaded a file yet" is wrong once eight
    have. The step must say which one is outstanding."""
    runs = [_run(f"report_{i}") for i in range(8)]
    step = doctor._check_real_run(runs, NINE)
    assert step.state == TODO
    assert "8 of 9" in step.why
    assert "report_8" in step.why


def test_all_reports_uploaded_completes_the_step():
    runs = [_run(f"report_{i}") for i in range(9)]
    assert doctor._check_real_run(runs, NINE).state == DONE


def test_a_skipped_upload_counts_as_done():
    """"Already in the folder for today" means the upload happened earlier."""
    runs = [_run(f"report_{i}", status="skipped") for i in range(9)]
    assert doctor._check_real_run(runs, NINE).state == DONE


def test_a_dry_run_never_completes_the_real_run_step():
    runs = [_run(f"report_{i}", dry=True) for i in range(9)]
    assert doctor._check_real_run(runs, NINE).state == TODO


def test_a_success_without_a_drive_id_does_not_count():
    runs = [_run(f"report_{i}", drive=None) for i in range(9)]
    assert doctor._check_real_run(runs, NINE).state == TODO


def test_dry_run_progress_is_tracked_per_report():
    runs = [_run(f"report_{i}", dry=True) for i in range(5)]
    step = doctor._check_dry_run(runs, NINE)
    assert step.state == TODO
    assert "5 of 9" in step.why


def test_only_a_handful_of_missing_reports_are_listed():
    """Nine slugs on one line is unreadable; the list truncates."""
    step = doctor._check_real_run([], NINE)
    assert step.state == TODO
    step = doctor._check_real_run([_run("report_0")], NINE)
    assert step.why.endswith("...")


# -- which browser to drive -------------------------------------------------

def test_a_configured_installed_browser_satisfies_the_step(monkeypatch):
    """On a macOS Playwright no longer builds Chromium for, an installed
    Chrome is the answer — and the step must recognise it."""
    monkeypatch.setattr(doctor.Path, "exists", lambda self: True)
    step = doctor._check_browser("chrome")
    assert step.state == DONE
    assert "Google Chrome" in step.name


def test_a_configured_browser_that_is_not_installed_is_reported(monkeypatch):
    monkeypatch.setattr(doctor.Path, "exists", lambda self: False)
    step = doctor._check_browser("chrome")
    assert step.state == TODO
    assert "not in your Applications folder" in step.why


def test_an_unknown_configured_browser_is_reported(monkeypatch):
    step = doctor._check_browser("safari")
    assert step.state == TODO
    assert "not a browser this tool knows how to find" in step.why


def test_an_installed_browser_is_suggested_before_a_download(monkeypatch, tmp_path):
    """The bug this replaces: with no Chromium on disk it told the operator to
    run `playwright install chromium` — the exact command that fails on their
    macOS. Never suggest a command that cannot succeed."""
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(doctor.Path, "exists", lambda self: True)
    step = doctor._check_browser("")
    assert step.state == TODO
    assert "BROWSER_CHANNEL=chrome" in step.command
    assert "playwright install" not in step.command


def test_downloading_is_only_suggested_when_nothing_is_installed(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(doctor.Path, "exists", lambda self: False)
    step = doctor._check_browser("")
    assert step.state == TODO
    assert "playwright install chromium" in step.command


def test_editing_commands_carry_an_absolute_path(tmp_path):
    """A bare "open .env" runs against whatever directory the shell is in,
    which after the installer is the home folder, not the project."""
    (tmp_path / ".env").write_text("REPORT_SLUG=TODO_X\n", encoding="utf-8")
    step = doctor._check_env(tmp_path)
    assert step.state == TODO
    assert str(tmp_path / ".env") in step.command


def test_outstanding_google_settings_do_not_block_the_portal_work(tmp_path):
    """Google is only needed for the upload. Reporting .env unfinished while
    the only gaps are Drive settings sends someone into the Cloud Console
    before the part that actually needs discovering — the portal."""
    (tmp_path / ".env").write_text(
        "EXTENDEDREACH_BASE_URL=https://real.example.com\n"
        "GOOGLE_DRIVE_FOLDER_ID=TODO_DRIVE_FOLDER_ID\n"
        "GOOGLE_TOKEN_FILE=/Users/TODO_YOU/er-sync/token.json\n",
        encoding="utf-8")
    step = doctor._check_env(tmp_path)
    assert step.state == DONE
    assert "2 Google setting" in step.detail


def test_a_non_google_todo_still_blocks(tmp_path):
    (tmp_path / ".env").write_text(
        "EXTENDEDREACH_BASE_URL=https://TODO.example.com\n"
        "GOOGLE_DRIVE_FOLDER_ID=TODO_DRIVE_FOLDER_ID\n",
        encoding="utf-8")
    assert doctor._check_env(tmp_path).state == TODO


def test_the_dry_run_comes_before_the_google_step(capsys):
    """Ordering is the point of this change: prove the export works, then wire
    up the destination. Google first sends someone into the Cloud Console
    before touching the part that actually needs discovering."""
    doctor.run_doctor()
    lines = capsys.readouterr().out.splitlines()
    dry = next(i for i, l in enumerate(lines) if "Test run passed" in l)
    google = next(i for i, l in enumerate(lines) if "Google OAuth" in l)
    assert dry < google
