"""`--doctor`: where am I, and what is the one next thing to run?

A list of seven setup steps is hard to hold in your head, and `--validate-config`
answers "what is wrong" rather than "what do I do now". This walks the steps in
order, stops at the first one that is not done, and prints one command.

Every check is a fact about the filesystem or the run log. Nothing here guesses.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

DONE = "done"
TODO = "todo"
SKIP = "n/a"


@dataclass
class Step:
    name: str
    state: str
    why: str = ""              # shown when the step is not done
    command: str = ""          # the one thing to run next
    detail: str = ""           # extra context, shown either way


def _venv_python() -> str:
    """The interpreter to put in printed commands, as the operator would type it."""
    return "./.venv/bin/python"


def _check_dependencies() -> Step:
    missing = []
    for module, label in (("playwright", "playwright"),
                          ("dotenv", "python-dotenv"),
                          ("googleapiclient", "google-api-python-client"),
                          ("openpyxl", "openpyxl"),
                          ("apscheduler", "APScheduler")):
        try:
            __import__(module)
        except ImportError:
            missing.append(label)
    if missing:
        return Step("Python dependencies installed", TODO,
                    why=f"missing: {', '.join(missing)}",
                    command="./scripts/install_playwright.sh")
    return Step("Python dependencies installed", DONE)


def _check_browser() -> Step:
    """Look for a downloaded Chromium on disk.

    Deliberately a filesystem check rather than starting Playwright: starting
    the driver just to ask a question leaves an async teardown traceback on
    stderr, and a confusing traceback in a "what do I do next" tool is worse
    than a slightly less authoritative answer. A genuine version mismatch is
    reported clearly at run time anyway.
    """
    try:
        import playwright  # noqa: F401
    except ImportError:
        return Step("Chromium downloaded", TODO,
                    why="playwright is not installed yet",
                    command="./scripts/install_playwright.sh")

    override = os.getenv("PLAYWRIGHT_BROWSERS_PATH")
    candidates = []
    if override and override not in {"0", "false"}:
        candidates.append(Path(override))
    candidates += [
        Path.home() / "Library" / "Caches" / "ms-playwright",   # macOS
        Path.home() / ".cache" / "ms-playwright",               # Linux
    ]

    for directory in candidates:
        try:
            if directory.is_dir() and any(directory.glob("chromium-*")):
                return Step("Chromium downloaded", DONE)
        except OSError:
            continue

    return Step("Chromium downloaded", TODO,
                why="no downloaded Chromium found",
                command="./.venv/bin/playwright install chromium")


def _check_env(root: Path) -> Step:
    path = root / ".env"
    if not path.exists():
        return Step(".env created", TODO,
                    why="the file does not exist yet",
                    command="cp .env.example .env    # then open it and fill in the TODOs")
    text = path.read_text(encoding="utf-8", errors="replace")
    todos = sum(1 for line in text.splitlines()
                if "TODO" in line and not line.strip().startswith("#"))
    if todos:
        return Step(".env filled in", TODO,
                    why=f"{todos} setting(s) still contain a TODO placeholder",
                    command="open .env    # replace every TODO")
    return Step(".env filled in", DONE)


def _check_workflow(root: Path) -> Step:
    path = root / "config" / "workflow.json"
    if not path.exists():
        draft = root / "config" / "workflow.draft.json"
        if draft.exists():
            return Step("workflow.json in place", TODO,
                        why="a draft exists but has not been promoted",
                        command="cp config/workflow.draft.json config/workflow.json")
        return Step("workflow.json in place", TODO,
                    why="the report URL and selectors have not been captured",
                    command=f"{_venv_python()} -m src.main --setup-assist")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return Step("workflow.json in place", TODO,
                    why="the file is not valid JSON",
                    command=f"{_venv_python()} -m src.main --setup-assist")
    # The example file's "$comment" blocks describe the placeholders, so they
    # contain the word TODO by design. Checking them would make this step
    # impossible to complete.
    def without_comments(node):
        if isinstance(node, dict):
            return {k: without_comments(v) for k, v in node.items()
                    if not k.startswith("$")}
        if isinstance(node, list):
            return [without_comments(v) for v in node]
        return node

    blob = json.dumps(without_comments(data))
    if "TODO" in blob:
        return Step("workflow.json filled in", TODO,
                    why="it still contains TODO placeholders",
                    command="open config/workflow.json")
    return Step("workflow.json filled in", DONE)


def _check_config(cfg, load_error: Optional[str]) -> Step:
    if load_error:
        return Step("Configuration valid", TODO, why=load_error,
                    command=f"{_venv_python()} -m src.main --validate-config")
    from src import config as config_module
    problems = config_module.validate(cfg, require_drive=True)
    errors = [p for p in problems if p.severity == "error"]
    if errors:
        return Step("Configuration valid", TODO,
                    why=f"{len(errors)} problem(s), including {errors[0].key}",
                    command=f"{_venv_python()} -m src.main --validate-config")
    return Step("Configuration valid", DONE)


def _check_google(cfg) -> Step:
    if cfg is None or cfg.google_credentials_file is None:
        return Step("Google OAuth client saved", TODO,
                    why="GOOGLE_CREDENTIALS_FILE is not set",
                    command="see README - Authorise Google Drive")
    if not Path(cfg.google_credentials_file).exists():
        return Step("Google OAuth client saved", TODO,
                    why="the credentials file is not at the configured path",
                    command="see README - Authorise Google Drive")
    token = Path(cfg.google_token_file) if cfg.google_token_file else None
    if token and token.exists():
        return Step("Google Drive authorised", DONE)
    return Step("Google OAuth client saved", DONE,
                detail="you will be asked to approve access on the first real run")


def _load_runs(cfg) -> list[dict]:
    if cfg is None:
        return []
    path = cfg.log_dir / "runs.jsonl"
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _succeeded_slugs(runs: list[dict], *, dry: bool) -> set[str]:
    """Reports that have completed successfully, one way or the other.

    A skipped run counts: "already in the folder for today" means the upload
    happened, on an earlier run.
    """
    good = {"success"} if dry else {"success", "skipped"}
    return {
        r.get("report_slug", "")
        for r in runs
        if r.get("status") in good
        and bool(r.get("dry_run")) == dry
        and (dry or r.get("drive_file_id"))
    }


def _check_dry_run(runs: list[dict], expected: Optional[set[str]] = None) -> Step:
    done = _succeeded_slugs(runs, dry=True)
    if expected:
        missing = expected - done
        if not missing:
            return Step(f"Test run passed for all {len(expected)} report(s)", DONE)
        if done:
            return Step("Test run passed (no upload)", TODO,
                        why=f"{len(done)} of {len(expected)} report(s) have "
                            f"passed a dry run; still to prove: "
                            f"{', '.join(sorted(missing)[:4])}"
                            + (" ..." if len(missing) > 4 else ""),
                        command="./scripts/run_once.sh --dry-run")
    elif done:
        return Step("Test run passed (no upload)", DONE)
    return Step("Test run passed (no upload)", TODO,
                why="no dry run has completed successfully yet",
                command="./scripts/run_once.sh --dry-run",
                detail="opens a browser; you sign in; downloads and checks the "
                       "files but uploads nothing")


def _check_real_run(runs: list[dict], expected: Optional[set[str]] = None) -> Step:
    done = _succeeded_slugs(runs, dry=False)
    if expected:
        missing = expected - done
        if not missing:
            return Step(f"All {len(expected)} report(s) reached Google Drive", DONE)
        if done:
            return Step("Every report reached Google Drive", TODO,
                        why=f"{len(done)} of {len(expected)} uploaded; still to "
                            f"land: {', '.join(sorted(missing)[:4])}"
                            + (" ..." if len(missing) > 4 else ""),
                        command="./scripts/run_once.sh")
    elif done:
        return Step("Real run reached Google Drive", DONE)
    return Step("Real run reached Google Drive", TODO,
                why="no run has uploaded a file yet",
                command="./scripts/run_once.sh")


def _check_schedule() -> Step:
    if sys.platform != "darwin":
        return Step("Schedule installed", SKIP,
                    detail="launchd is macOS-only; this machine is not a Mac")
    plist = Path.home() / "Library" / "LaunchAgents" / \
        "com.agency.extendedreach-report-sync.plist"
    if plist.exists():
        return Step("Schedule installed", DONE)
    return Step("Schedule installed", TODO,
                why="the job does not run on its own yet",
                command="./scripts/install_schedule.sh daily")


def run_doctor(env_file: Optional[str] = None) -> int:
    """Print the checklist and the single next command. Always exits 0 —
    this is a status report, not a gate."""
    from src import config as config_module

    root = Path(__file__).resolve().parent.parent

    cfg = None
    load_error = None
    try:
        cfg = config_module.load(env_file=env_file)
    except config_module.ConfigError as exc:
        load_error = str(exc).splitlines()[0]
    except Exception as exc:
        load_error = type(exc).__name__

    runs = _load_runs(cfg)
    expected = ({r.slug for r in cfg.enabled_reports()} if cfg else set()) or None

    steps = [
        _check_dependencies(),
        _check_browser(),
        _check_env(root),
        _check_workflow(root),
        _check_config(cfg, load_error),
        _check_google(cfg),
        _check_dry_run(runs, expected),
        _check_real_run(runs, expected),
        _check_schedule(),
    ]

    print("\n  Setup checklist\n")
    marks = {DONE: "[x]", TODO: "[ ]", SKIP: "[-]"}
    for index, step in enumerate(steps, start=1):
        print(f"  {marks[step.state]} {index}. {step.name}")
        if step.state == TODO and step.why:
            print(f"          {step.why}")
        if step.detail:
            print(f"          {step.detail}")

    remaining = [s for s in steps if s.state == TODO]
    done = sum(1 for s in steps if s.state == DONE)
    total = sum(1 for s in steps if s.state != SKIP)

    print(f"\n  {done} of {total} done.\n")

    if not remaining:
        print("  Everything is set up. It will run on its own from here.")
        print("  Check on it with:\n")
        print(f"      {_venv_python()} -m src.main --status\n")
        return 0

    nxt = remaining[0]
    print("  NEXT — run this one command:\n")
    print(f"      {nxt.command}\n")
    if len(remaining) > 1:
        print(f"  ({len(remaining) - 1} step(s) after that. Run --doctor again "
              f"any time to see where you are.)\n")

    # An expired session is the one condition that undoes finished steps.
    if runs and runs[-1].get("status") == "requires_human_login":
        print("  NOTE: the last run stopped because the portal session expired.")
        print("  One headed run signs it back in: ./scripts/run_once.sh\n")

    return 0
