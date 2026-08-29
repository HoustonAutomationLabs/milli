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


def _editor_command(path: Path) -> str:
    """How to open a file for editing, from any directory.

    Absolute paths on purpose: the installer's Terminal window ends in the home
    directory, so a relative path there reports the file missing and reads as
    though the install failed.
    """
    import shutil

    if shutil.which("code"):
        return f'code "{path}"'
    return f'open -e "{path}"'



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


# Browsers already on the machine that Playwright can drive directly.
INSTALLED_BROWSERS = {
    "chrome": Path("/Applications/Google Chrome.app"),
    "chrome-beta": Path("/Applications/Google Chrome Beta.app"),
    "msedge": Path("/Applications/Microsoft Edge.app"),
}


def _check_browser(channel: str = "") -> Step:
    """Confirm there is a browser to drive.

    Which browser depends on configuration. Playwright no longer builds its own
    Chromium for older macOS releases, so on those the answer is an installed
    Google Chrome and "download Chromium" is advice that cannot succeed —
    telling someone to run a command that will fail is worse than saying
    nothing.

    Deliberately a filesystem check rather than starting Playwright: starting
    the driver just to ask a question leaves an async teardown traceback on
    stderr, and a confusing traceback in a "what do I do next" tool is worse
    than a slightly less authoritative answer.
    """
    try:
        import playwright  # noqa: F401
    except ImportError:
        return Step("Browser ready", TODO,
                    why="playwright is not installed yet",
                    command="bash START-HERE.command")

    # Configured to drive an installed browser: check for that one instead.
    if channel:
        app = INSTALLED_BROWSERS.get(channel)
        if app is None:
            return Step("Browser ready", TODO,
                        why=f"BROWSER_CHANNEL is set to {channel!r}, which is "
                            "not a browser this tool knows how to find",
                        command="open .env")
        if app.exists():
            return Step(f"Browser ready ({app.stem})", DONE)
        return Step("Browser ready", TODO,
                    why=f"BROWSER_CHANNEL is set to {channel!r} but "
                        f"{app.name} is not in your Applications folder",
                    command="install it from google.com/chrome")

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
                return Step("Browser ready (Chromium)", DONE)
        except OSError:
            continue

    # No downloaded Chromium. Before sending anyone off to download one, check
    # whether this machine already has a browser that would work — on a macOS
    # Playwright has dropped, the download is not merely slow, it is refused.
    for name, app in INSTALLED_BROWSERS.items():
        if app.exists():
            return Step("Browser ready", TODO,
                        why=f"no downloaded Chromium, but {app.stem} is "
                            "installed and can be used instead",
                        command=f"add this line to .env:  BROWSER_CHANNEL={name}",
                        detail="required on macOS versions Playwright no longer "
                               "builds its own browser for; harmless otherwise")

    return Step("Browser ready", TODO,
                why="no browser found to drive",
                command="./.venv/bin/python -m playwright install chromium")


def _check_env(root: Path) -> Step:
    path = root / ".env"
    if not path.exists():
        return Step(".env created", TODO,
                    why="the file does not exist yet",
                    command=f'cp "{root}/.env.example" "{path}"')
    text = path.read_text(encoding="utf-8", errors="replace")
    live = [line for line in text.splitlines()
            if "TODO" in line and not line.strip().startswith("#")]
    google_only = live and all("GOOGLE" in line.upper() for line in live)

    if live and google_only:
        # Google is not needed to prove the export works, and saying so here
        # saves an evening of Cloud Console clicking before the part that
        # actually needs discovering.
        return Step(".env filled in (except Google)", DONE,
                    detail=f"{len(live)} Google setting(s) still to do — they "
                           f"are only needed for the upload, which comes later")
    if live:
        return Step(".env filled in", TODO,
                    why=f"{len(live)} setting(s) still contain a TODO placeholder",
                    command=_editor_command(path))
    return Step(".env filled in", DONE)


def _check_workflow(root: Path) -> Step:
    path = root / "config" / "workflow.json"
    if not path.exists():
        draft = root / "config" / "workflow.draft.json"
        if draft.exists():
            return Step("workflow.json in place", TODO,
                        why="a draft exists but has not been promoted",
                        command=f'cp "{draft}" "{path}"')
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

    cleaned = without_comments(data)
    # An empty authenticated_selector is the supported default, not a gap.
    cleaned.get("auth", {}).pop("authenticated_selector", None)
    blob = json.dumps(cleaned)
    if "TODO" in blob:
        return Step("workflow.json filled in", TODO,
                    why="it still contains TODO placeholders",
                    command=_editor_command(path))
    return Step("workflow.json filled in", DONE)


def _check_config(cfg, load_error: Optional[str]) -> Step:
    if load_error:
        return Step("Configuration valid", TODO, why=load_error,
                    command=f"{_venv_python()} -m src.main --validate-config")
    from src import config as config_module
    # require_drive=False: Drive settings are checked by their own step, which
    # now comes after the dry run. A missing folder id should not report the
    # whole configuration invalid while the operator is still working on the
    # portal half.
    problems = config_module.validate(cfg, require_drive=False)
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
        _check_browser(cfg.browser_channel if cfg else ""),
        _check_env(root),
        _check_workflow(root),
        _check_config(cfg, load_error),
        _check_dry_run(runs, expected),
        _check_google(cfg),
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
    if nxt.command.startswith("./"):
        # Relative commands only work inside the project. Say where that is,
        # because the window this was printed in is usually somewhere else.
        print(f"  (from {root} — if you are elsewhere, run first:)")
        print(f"      cd \"{root}\"\n")
    if len(remaining) > 1:
        print(f"  ({len(remaining) - 1} step(s) after that. Run --doctor again "
              f"any time to see where you are.)\n")

    # An expired session is the one condition that undoes finished steps.
    if runs and runs[-1].get("status") == "requires_human_login":
        print("  NOTE: the last run stopped because the portal session expired.")
        print("  One headed run signs it back in: ./scripts/run_once.sh\n")

    return 0
