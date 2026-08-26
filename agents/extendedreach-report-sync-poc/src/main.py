#!/usr/bin/env python3
"""extendedreach-report-sync-poc — CLI entry point.

One authorised, read-only workflow: open a report in an already-authenticated
browser profile, export it, validate the file, and upload it to one Google
Drive folder if it has not been uploaded already.

    python -m src.main --doctor
    python -m src.main --setup-assist
    python -m src.main --validate-config
    python -m src.main --test-download-fixture
    python -m src.main --once --dry-run
    python -m src.main --once
    python -m src.main --schedule
    python -m src.main --status

Exit codes are meaningful so a scheduler can alert on them; see EXIT_* below.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Absolute imports throughout, with the project root forced onto sys.path, so
# `python -m src.main` and `python src/main.py` behave identically. Relative
# imports would work only under the first form, and the difference would not
# show up until the one code path that used them was reached.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as config_module          # noqa: E402
from src import fixtures, logging_utils, validators   # noqa: E402
from src.drive_uploader import DriveError, DriveUploader   # noqa: E402

EXIT_OK = 0
EXIT_UNEXPECTED = 1
EXIT_CONFIG_INVALID = 2
EXIT_REQUIRES_HUMAN_LOGIN = 3
EXIT_VALIDATION_FAILED = 4
EXIT_DOWNLOAD_FAILED = 5
EXIT_UPLOAD_FAILED = 6
EXIT_ALREADY_RUNNING = 7

LOCK_NAME = "er_sync.lock"


# ---------------------------------------------------------------------------
# Single-instance lock
# ---------------------------------------------------------------------------

class SingleInstance:
    """A flock on a file in the log directory.

    launchd will happily start a second copy while the first is still holding
    a browser open on the same profile, which corrupts the profile. This makes
    the second copy exit quietly instead.
    """

    def __init__(self, path: Path):
        self.path = path
        self._handle = None

    def __enter__(self) -> "SingleInstance":
        import fcntl
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w")
        try:
            fcntl.flock(self._handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._handle.close()
            self._handle = None
            raise RuntimeError("another run holds the lock")
        self._handle.write(str(os.getpid()))
        self._handle.flush()
        return self

    def __exit__(self, *exc_info) -> None:
        import fcntl
        if self._handle:
            try:
                fcntl.flock(self._handle, fcntl.LOCK_UN)
            finally:
                self._handle.close()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_validate_config(args) -> int:
    """Check configuration without opening a browser or touching the network."""
    try:
        cfg = config_module.load(env_file=args.env_file)
    except config_module.ConfigError as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    problems = config_module.validate(cfg, require_drive=not args.dry_run)
    errors = [p for p in problems if p.severity == "error"]
    warnings = [p for p in problems if p.severity == "warning"]

    print(f"\nProject : extendedreach-report-sync-poc")
    print(f"Report  : {cfg.report_slug or '(not set)'}")
    print(f"Workflow: {cfg.workflow_path.name if cfg.workflow_path else '(not set)'}")
    print(f"Portal  : {logging_utils.safe_url(cfg.base_url) or '(not set)'}")
    print(f"Drive   : folder {'set' if cfg.drive_folder_id and 'TODO' not in cfg.drive_folder_id else 'NOT SET'}")
    print()

    if warnings:
        print("Warnings (run will proceed):")
        print(config_module.format_problems(warnings))
        print()
    if errors:
        print("Errors (run is blocked):")
        print(config_module.format_problems(errors))
        print(f"\n{len(errors)} error(s). Fix these before running --once.\n")
        return EXIT_CONFIG_INVALID

    print("Configuration is complete and internally consistent.")
    print("Note: this checks the shape of the configuration only. Nothing here")
    print("proves the selectors match the live portal — only a headed run")
    print("against the authorised account can show that.\n")
    return EXIT_OK


def cmd_test_fixture(args) -> int:
    """Validate sample files with no access to ExtendedReach at all."""
    headers = ["Case #", "Task", "Due Date", "Status"]
    try:
        cfg = config_module.load(env_file=args.env_file)
        if cfg.expected_csv_headers and not any(
                "TODO" in h for h in cfg.expected_csv_headers):
            headers = cfg.expected_csv_headers
        min_bytes = cfg.min_file_bytes
        encodings = cfg.csv_encodings
        allowed = cfg.allowed_extensions
    except config_module.ConfigError:
        min_bytes, encodings = 1024, ["utf-8-sig", "cp1252"]
        allowed = set(validators.APPROVED_EXTENSIONS)

    directory = Path(args.fixture_dir).expanduser() if args.fixture_dir else \
        Path(os.getenv("TMPDIR", "/tmp")) / "er-sync-fixtures"

    if args.fixture_dir and directory.exists() and any(directory.iterdir()):
        paths = sorted(p for p in directory.iterdir() if p.is_file())
        print(f"\nValidating {len(paths)} existing file(s) in {directory}\n")
    else:
        paths = fixtures.build_fixture_set(directory, headers)
        print(f"\nGenerated {len(paths)} synthetic sample(s) in {directory}")
        print("These are invented values, not an ExtendedReach export.\n")

    print(f"Rules: min {min_bytes} bytes, extensions {sorted(allowed)}")
    print(f"       required CSV headers {headers}\n")

    expected_failures = {"sample_truncated.csv", "sample_error_page.xlsx"}
    unexpected = 0
    for path in paths:
        result = validators.validate_file(
            path,
            min_bytes=min_bytes,
            allowed_extensions=allowed,
            expected_csv_headers=headers,
            csv_encodings=encodings,
        )
        mark = "PASS" if result.ok else "FAIL"
        detail = "" if result.ok else f"  <- {result.category}"
        print(f"  {mark}  {path.name:32}{detail}")
        should_fail = path.name in expected_failures
        if result.ok == should_fail:
            unexpected += 1

    print()
    if unexpected:
        print(f"{unexpected} file(s) did not behave as expected.\n")
        return EXIT_VALIDATION_FAILED
    print("Validation logic behaves correctly on every sample, including the")
    print("two that must fail: a truncated export and an HTML error page")
    print("saved with a report extension.\n")
    return EXIT_OK


def cmd_once(args) -> int:
    """One export: navigate, download, validate, upload."""
    started = datetime.now()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    try:
        cfg = config_module.load(env_file=args.env_file)
        config_module.require_valid(cfg, require_drive=not args.dry_run)
    except config_module.ConfigError as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    logging_utils.configure_extra_terms(cfg.redact_terms)
    log = logging_utils.get_logger("er_sync", cfg.log_dir, verbose=args.verbose)

    record = logging_utils.RunRecord(
        run_id=run_id,
        report_slug=cfg.report_slug,
        started_at=started.astimezone(timezone.utc).isoformat(timespec="seconds"),
        run_key=validators.build_run_key(cfg.report_slug, started),
        dry_run=args.dry_run,
    )

    for warning in cfg.warnings:
        log.warning("%s", warning)
        record.note(str(warning))

    try:
        with SingleInstance(cfg.log_dir / LOCK_NAME):
            return _run_workflow(cfg, args, log, record, started)
    except RuntimeError:
        # Another instance is running. Not a failure — the scheduler overlapped.
        log.warning("Another run is already in progress; exiting")
        record.finish(logging_utils.STATUS_SKIPPED, "another_run_in_progress")
        logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_ALREADY_RUNNING


def _run_workflow(cfg, args, log, record, started) -> int:
    # Imported here so --validate-config and --test-download-fixture work
    # without Playwright installed.
    try:
        from src.browser_worker import (
            BrowserWorker,
            BrowserWorkerError,
            RequiresHumanLogin,
        )
    except ImportError:
        log.error("Playwright is not installed; run scripts/install_playwright.sh")
        record.finish(logging_utils.STATUS_FAILED, "playwright_not_installed")
        logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_CONFIG_INVALID

    log.info("Run %s starting for report '%s'%s",
             record.run_id, cfg.report_slug, " (dry run)" if args.dry_run else "")

    download = None
    worker: Optional[BrowserWorker] = None

    try:
        with BrowserWorker(cfg, log, headed=args.headed) as worker:
            worker.ensure_authenticated()
            worker.navigate_to_report()
            worker.apply_filters()
            download = worker.download_report(when=started)

    except RequiresHumanLogin as exc:
        log.error("Stopped: a person must complete sign-in")
        record.finish(logging_utils.STATUS_REQUIRES_HUMAN_LOGIN, exc.category)
        logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_REQUIRES_HUMAN_LOGIN

    except BrowserWorkerError as exc:
        log.error("Browser step failed (%s)", exc.category)
        record.note(exc.detail)
        record.finish(logging_utils.STATUS_FAILED, exc.category)
        logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_DOWNLOAD_FAILED

    except Exception as exc:
        log.error("Unexpected browser failure (%s)", type(exc).__name__)
        record.finish(logging_utils.STATUS_FAILED, "unexpected_browser_error")
        logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_UNEXPECTED

    record.local_filename = download.filename
    log.info("Validating the downloaded file")

    result = validators.validate_file(
        download.path,
        min_bytes=cfg.min_file_bytes,
        allowed_extensions=cfg.allowed_extensions,
        expected_csv_headers=cfg.expected_csv_headers,
        csv_encodings=cfg.csv_encodings,
    )
    if not result.ok:
        log.error("Validation failed (%s): %s", result.category, result.detail)
        record.note(f"checks passed before failure: {result.checks}")
        record.finish(logging_utils.STATUS_FAILED, result.category)
        logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_VALIDATION_FAILED

    log.info("Validation passed (%s)", ", ".join(result.checks))

    if args.dry_run:
        log.info("Dry run: the file was downloaded and validated but NOT uploaded")
        record.note("dry run — upload skipped")
        record.finish(logging_utils.STATUS_SUCCESS)
        logging_utils.write_run_record(cfg.log_dir, record)
        _print_summary(record, cfg)
        return EXIT_OK

    # -- upload ------------------------------------------------------------
    uploader = DriveUploader(cfg, log)
    run_key = record.run_key or validators.build_run_key(cfg.report_slug, started)
    prefix = validators.filename_prefix_for_run_key(cfg.report_slug, started)

    try:
        existing = uploader.find_existing(cfg.drive_folder_id, run_key, prefix)
        if existing:
            log.info("A file for this run key is already in the folder; skipping upload")
            record.drive_file_id = existing.file_id
            record.finish(logging_utils.STATUS_SKIPPED, "duplicate_run_key")
            logging_utils.write_run_record(cfg.log_dir, record)
            _print_summary(record, cfg)
            return EXIT_OK

        record.drive_file_id = uploader.upload(
            download.path, cfg.drive_folder_id, run_key, cfg.report_slug)

    except DriveError as exc:
        log.error("Drive step failed (%s)", exc.category)
        record.note(exc.detail)
        record.finish(logging_utils.STATUS_FAILED, exc.category)
        logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_UPLOAD_FAILED

    record.finish(logging_utils.STATUS_SUCCESS)
    logging_utils.write_run_record(cfg.log_dir, record)
    _print_summary(record, cfg)
    return EXIT_OK


def _print_summary(record, cfg) -> None:
    print("\n" + "-" * 60)
    print(f"  run id     {record.run_id}")
    print(f"  report     {record.report_slug}")
    print(f"  status     {record.status}")
    print(f"  file       {record.local_filename or '(none)'}")
    print(f"  drive id   {record.drive_file_id or '(not uploaded)'}")
    print(f"  log        {cfg.log_dir / 'runs.jsonl'}")
    print("-" * 60 + "\n")


def cmd_doctor(args) -> int:
    """Where am I in setup, and what is the one next command?"""
    from src.doctor import run_doctor
    return run_doctor(env_file=args.env_file)


def cmd_setup_assist(args) -> int:
    """Capture the report URL and candidate selectors, with you driving."""
    try:
        cfg = config_module.load(env_file=args.env_file)
    except config_module.ConfigError as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    if not cfg.base_url or "TODO" in cfg.base_url:
        print("\nSet EXTENDEDREACH_BASE_URL in .env first — the assistant "
              "needs to know which portal to open.\n", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    logging_utils.configure_extra_terms(cfg.redact_terms)
    log = logging_utils.get_logger("er_sync", cfg.log_dir, verbose=args.verbose)

    try:
        from src.setup_assist import run_setup_assist
    except ImportError:
        print("\nPlaywright is not installed; run scripts/install_playwright.sh\n",
              file=sys.stderr)
        return EXIT_CONFIG_INVALID

    project_root = Path(__file__).resolve().parent.parent
    out_path = project_root / "config" / "workflow.draft.json"
    try:
        return run_setup_assist(cfg, log, out_path)
    except KeyboardInterrupt:
        print("\nCancelled. Nothing was written.\n")
        return EXIT_OK
    except Exception as exc:
        log.error("Setup assistant failed (%s)", type(exc).__name__)
        return EXIT_UNEXPECTED


def cmd_status(args) -> int:
    """Show recent runs, so a silently failing schedule is visible.

    An empty Drive folder means either "nothing to upload" or "six failed
    runs". Only the run log tells them apart, and nobody reads a JSON Lines
    file by choice.
    """
    import json

    try:
        cfg = config_module.load(env_file=args.env_file)
    except config_module.ConfigError as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    path = cfg.log_dir / "runs.jsonl"
    if not path.exists():
        print(f"\nNo runs recorded yet ({path} does not exist).")
        print("That means the job has never run — not that it ran and found "
              "nothing.\n")
        return EXIT_OK

    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    limit = max(1, args.limit)
    recent = records[-limit:]

    print(f"\nLast {len(recent)} run(s) of {len(records)} recorded\n")
    print(f"  {'started':<20} {'status':<22} {'detail'}")
    print(f"  {'-' * 20} {'-' * 22} {'-' * 34}")
    for record in recent:
        started = (record.get("started_at") or "")[:19].replace("T", " ")
        status = record.get("status", "?")
        if record.get("dry_run"):
            status += " (dry)"
        detail = record.get("error_category") or record.get("drive_file_id") or ""
        print(f"  {started:<20} {status:<22} {detail}")

    # A summary aimed at the question actually being asked: is it working?
    last = recent[-1] if recent else {}
    successes = sum(1 for r in records if r.get("status") == "success")
    failures = [r for r in records if r.get("status") == "failed"]
    human = [r for r in records
             if r.get("status") == "requires_human_login"]

    print()
    if last.get("status") == "success":
        print("  Last run succeeded.")
    elif last.get("status") == "skipped":
        print("  Last run was skipped — already uploaded, or another run held "
              "the lock. Both are normal.")
    elif last.get("status") == "requires_human_login":
        print("  ACTION NEEDED: the saved session has expired.")
        print("  Run  ./scripts/run_once.sh  once, headed, and sign in.")
        print("  Until you do, the scheduled job will keep doing nothing.")
    elif last.get("status") == "failed":
        print(f"  ACTION NEEDED: the last run failed "
              f"({last.get('error_category')}).")

    print(f"\n  totals: {successes} success, {len(failures)} failed, "
          f"{len(human)} needing sign-in\n")
    return EXIT_OK


def cmd_schedule(args) -> int:
    """Optional local schedule. The same workflow --once runs."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    cfg = config_module.load(env_file=args.env_file)
    logging_utils.configure_extra_terms(cfg.redact_terms)
    log = logging_utils.get_logger("er_sync", cfg.log_dir, verbose=args.verbose)

    cron = args.cron or cfg.schedule_cron
    try:
        trigger = CronTrigger.from_crontab(cron)
    except ValueError:
        print(f"\nSCHEDULE_CRON is not a valid crontab expression: {cron!r}\n",
              file=sys.stderr)
        return EXIT_CONFIG_INVALID

    scheduler = BlockingScheduler()
    # max_instances=1 plus the file lock: APScheduler prevents overlap inside
    # this process, the lock prevents it across processes.
    scheduler.add_job(lambda: cmd_once(args), trigger,
                      id="er_sync", max_instances=1, coalesce=True)

    log.info("Scheduled '%s' — Ctrl-C to stop", cron)
    print(f"\nRunning on schedule: {cron}")
    print("For an unattended schedule on macOS prefer launchd; see")
    print("scripts/schedule_example.md. Ctrl-C to stop.\n")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped")
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="extendedreach-report-sync-poc",
        description="Authorised, read-only ExtendedReach report export to Google Drive.",
        epilog="This tool never creates, edits, approves, rejects, submits or "
               "deletes anything in the portal.",
    )

    command = parser.add_mutually_exclusive_group()
    command.add_argument("--once", action="store_true",
                         help="run one export workflow (default)")
    command.add_argument("--validate-config", action="store_true",
                         help="check configuration without opening a browser")
    command.add_argument("--test-download-fixture", action="store_true",
                         help="validate sample files without touching ExtendedReach")
    command.add_argument("--schedule", action="store_true",
                         help="run on the local APScheduler schedule")
    command.add_argument("--setup-assist", action="store_true",
                         help="open the portal and capture the report URL and "
                              "selectors; you drive, it clicks nothing")
    command.add_argument("--status", action="store_true",
                         help="show recent runs and whether anything needs you")
    command.add_argument("--doctor", action="store_true",
                         help="show the setup checklist and the one next command")

    headed = parser.add_mutually_exclusive_group()
    headed.add_argument("--headed", dest="headed", action="store_true", default=True,
                        help="visible browser (default; required for first sign-in)")
    headed.add_argument("--headless", dest="headed", action="store_false",
                        help="no window; fails with requires_human_login if "
                             "the profile has no live session")

    parser.add_argument("--dry-run", action="store_true",
                        help="download and validate, but never upload to Drive")
    parser.add_argument("--fixture-dir", default=None,
                        help="directory of sample files for --test-download-fixture")
    parser.add_argument("--env-file", default=None, help="path to a .env file")
    parser.add_argument("--cron", default=None,
                        help="crontab expression for --schedule (overrides .env)")
    parser.add_argument("--limit", type=int, default=10,
                        help="how many runs --status shows (default 10)")
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if args.validate_config:
        return cmd_validate_config(args)
    if args.test_download_fixture:
        return cmd_test_fixture(args)
    if args.doctor:
        return cmd_doctor(args)
    if args.setup_assist:
        return cmd_setup_assist(args)
    if args.status:
        return cmd_status(args)
    if args.schedule:
        return cmd_schedule(args)
    return cmd_once(args)


if __name__ == "__main__":
    sys.exit(main())
