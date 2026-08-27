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
from typing import Any, Optional

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

    reports = cfg.selected_reports(args.report)
    if not reports:
        if args.report:
            known = ", ".join(sorted(cfg.reports)) or "none"
            print(f"\nNo report named {args.report!r}. Configured: {known}\n",
                  file=sys.stderr)
        else:
            print("\nNo reports are enabled in the workflow file.\n",
                  file=sys.stderr)
        return EXIT_CONFIG_INVALID

    # One record per report. They share a run id so a single scheduled run can
    # be read back as a unit, and each carries its own outcome.
    started_utc = started.astimezone(timezone.utc).isoformat(timespec="seconds")
    records = {
        report.slug: logging_utils.RunRecord(
            run_id=run_id,
            report_slug=report.slug,
            started_at=started_utc,
            run_key=validators.build_run_key(report.slug, started),
            dry_run=args.dry_run,
        )
        for report in reports
    }

    for warning in cfg.warnings:
        log.warning("%s", warning)

    try:
        with SingleInstance(cfg.log_dir / LOCK_NAME):
            return _run_workflow(cfg, args, log, records, started)
    except RuntimeError:
        # Another instance is running. Not a failure — the scheduler overlapped.
        log.warning("Another run is already in progress; exiting")
        for record in records.values():
            record.finish(logging_utils.STATUS_SKIPPED, "another_run_in_progress")
            logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_ALREADY_RUNNING


def _run_workflow(cfg, args, log, records, started) -> int:
    """Export every selected report in one browser session.

    One sign-in covers all of them, which matters at nine reports: opening and
    closing a browser nine times would mean nine chances for the session check
    to be the thing that fails.

    A failure on one report never loses the others. The run continues and the
    exit code reports the worst outcome, so a scheduler still alerts.
    """
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
        for record in records.values():
            record.finish(logging_utils.STATUS_FAILED, "playwright_not_installed")
            logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_CONFIG_INVALID

    reports = cfg.selected_reports(args.report)
    log.info("Run %s starting: %d report(s)%s",
             records[reports[0].slug].run_id if reports else "-",
             len(reports), " (dry run)" if args.dry_run else "")

    downloads: dict[str, Any] = {}
    uploader = None if args.dry_run else DriveUploader(cfg, log)
    worst = EXIT_OK

    # ---- phase 1: one browser session, every report ----------------------
    try:
        with BrowserWorker(cfg, log, headed=args.headed) as worker:
            worker.ensure_authenticated()

            for report in reports:
                record = records[report.slug]
                log.info("[%s] navigating", report.slug)
                try:
                    worker.navigate_to_report(report)
                    worker.apply_filters(report)
                    downloads[report.slug] = worker.download_report(report, when=started)
                except BrowserWorkerError as exc:
                    # One report's broken selector must not cost the other eight.
                    log.error("[%s] failed (%s)", report.slug, exc.category)
                    record.note(exc.detail)
                    record.finish(logging_utils.STATUS_FAILED, exc.category)
                    worst = max(worst, EXIT_DOWNLOAD_FAILED)
                except Exception as exc:
                    log.error("[%s] unexpected failure (%s)",
                              report.slug, type(exc).__name__)
                    record.finish(logging_utils.STATUS_FAILED, "unexpected_browser_error")
                    worst = max(worst, EXIT_UNEXPECTED)

    except RequiresHumanLogin as exc:
        # Authentication is shared, so this ends every report at once.
        log.error("Stopped: a person must complete sign-in")
        for record in records.values():
            record.finish(logging_utils.STATUS_REQUIRES_HUMAN_LOGIN, exc.category)
            logging_utils.write_run_record(cfg.log_dir, record)
        return EXIT_REQUIRES_HUMAN_LOGIN

    except BrowserWorkerError as exc:
        log.error("Browser session failed (%s)", exc.category)
        for record in records.values():
            if record.status == logging_utils.STATUS_FAILED and record.error_category:
                continue
            record.finish(logging_utils.STATUS_FAILED, exc.category)
        _flush(cfg, records)
        return EXIT_DOWNLOAD_FAILED

    except Exception as exc:
        log.error("Unexpected browser failure (%s)", type(exc).__name__)
        for record in records.values():
            if record.error_category:
                continue
            record.finish(logging_utils.STATUS_FAILED, "unexpected_browser_error")
        _flush(cfg, records)
        return EXIT_UNEXPECTED

    # ---- phase 2: validate, then upload ---------------------------------
    for report in reports:
        record = records[report.slug]
        download = downloads.get(report.slug)
        if download is None:
            continue                     # already recorded as failed above

        record.local_filename = download.filename
        result = validators.validate_file(
            download.path,
            min_bytes=report.min_bytes(cfg.min_file_bytes),
            allowed_extensions=cfg.allowed_extensions,
            expected_csv_headers=report.expected_headers(cfg.expected_csv_headers),
            csv_encodings=cfg.csv_encodings,
        )
        if not result.ok:
            log.error("[%s] validation failed (%s): %s",
                      report.slug, result.category, result.detail)
            record.note(f"checks passed before failure: {result.checks}")
            record.finish(logging_utils.STATUS_FAILED, result.category)
            worst = max(worst, EXIT_VALIDATION_FAILED)
            continue

        log.info("[%s] validation passed (%s)", report.slug, ", ".join(result.checks))

        if args.dry_run:
            record.note("dry run - upload skipped")
            record.finish(logging_utils.STATUS_SUCCESS)
            continue

        folder = cfg.drive_folder_for(report)
        run_key = record.run_key or validators.build_run_key(report.slug, started)
        prefix = validators.filename_prefix_for_run_key(report.slug, started)
        try:
            existing = uploader.find_existing(folder, run_key, prefix)
            if existing:
                log.info("[%s] already in the folder for today; skipping upload",
                         report.slug)
                record.drive_file_id = existing.file_id
                record.finish(logging_utils.STATUS_SKIPPED, "duplicate_run_key")
                continue
            record.drive_file_id = uploader.upload(
                download.path, folder, run_key, report.slug)
            record.finish(logging_utils.STATUS_SUCCESS)
        except DriveError as exc:
            log.error("[%s] Drive step failed (%s)", report.slug, exc.category)
            record.note(exc.detail)
            record.finish(logging_utils.STATUS_FAILED, exc.category)
            worst = max(worst, EXIT_UPLOAD_FAILED)

    _flush(cfg, records)
    _print_multi_summary(records, cfg)
    return worst


def _flush(cfg, records) -> None:
    """Write every run record, finishing any that never reached an outcome."""
    for record in records.values():
        if record.ended_at is None:
            record.finish(logging_utils.STATUS_FAILED, "never_ran")
        logging_utils.write_run_record(cfg.log_dir, record)


def _print_multi_summary(records, cfg) -> None:
    rows = list(records.values())
    width = max((len(r.report_slug) for r in rows), default=10)
    print("\n" + "-" * 72)
    for record in rows:
        detail = record.drive_file_id or record.error_category or ""
        print(f"  {record.report_slug:<{width}}  {record.status:<22} {detail}")
    print("-" * 72)
    ok = sum(1 for r in rows if r.status == logging_utils.STATUS_SUCCESS)
    skipped = sum(1 for r in rows if r.status == logging_utils.STATUS_SKIPPED)
    failed = sum(1 for r in rows if r.status == logging_utils.STATUS_FAILED)
    print(f"  {ok} uploaded, {skipped} already there, {failed} failed "
          f"of {len(rows)} report(s)")
    print(f"  log  {cfg.log_dir / 'runs.jsonl'}")
    print("-" * 72 + "\n")


def cmd_list_reports(args) -> int:
    """Show every configured report and whether it is switched on."""
    try:
        cfg = config_module.load(env_file=args.env_file)
    except config_module.ConfigError as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    if not cfg.reports:
        print("\nNo reports are configured yet. Run --setup-assist to add one.\n")
        return EXIT_OK

    width = max(len(slug) for slug in cfg.reports)
    print(f"\n  {len(cfg.reports)} report(s) configured\n")
    print(f"  {'':3} {'slug':<{width}}  {'columns checked':<16} description")
    print(f"  {'':3} {'-' * width}  {'-' * 16} {'-' * 30}")
    for slug, report in cfg.reports.items():
        mark = "[x]" if report.enabled else "[ ]"
        headers = report.expected_headers(cfg.expected_csv_headers)
        checked = str(len(headers)) if headers else "none (size only)"
        print(f"  {mark} {slug:<{width}}  {checked:<16} {report.description[:34]}")

    print(f"\n  {len(cfg.enabled_reports())} enabled; these all run on each "
          f"scheduled run.")
    print("  Run one on its own with:  --once --report <slug>\n")
    return EXIT_OK


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
    live_path = project_root / "config" / "workflow.json"
    try:
        return run_setup_assist(cfg, log, out_path, slug=args.report,
                                live_path=live_path)
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

    # With nine reports a flat tail of the log shows one run and hides the
    # rest, so the default view is the latest outcome per report.
    latest: dict[str, dict] = {}
    for record in records:
        slug = record.get("report_slug", "?")
        latest[slug] = record

    if args.report:
        rows = [r for r in records if r.get("report_slug") == args.report]
        rows = rows[-max(1, args.limit):]
        title = f"Last {len(rows)} run(s) of {args.report}"
    else:
        rows = sorted(latest.values(), key=lambda r: r.get("report_slug", ""))
        title = f"Latest run of each of {len(rows)} report(s)"

    width = max((len(r.get("report_slug", "?")) for r in rows), default=12)
    print(f"\n{title}\n")
    print(f"  {'report':<{width}}  {'when':<17} {'status':<22} detail")
    print(f"  {'-' * width}  {'-' * 17} {'-' * 22} {'-' * 24}")
    for record in rows:
        slug = record.get("report_slug", "?")
        when = (record.get("started_at") or "")[5:16].replace("T", " ")
        status = record.get("status", "?")
        if record.get("dry_run"):
            status += " (dry)"
        detail = record.get("error_category") or record.get("drive_file_id") or ""
        print(f"  {slug:<{width}}  {when:<17} {status:<22} {detail}")

    # The summary answers the only question that matters: is anything stuck?
    needs_login = [s for s, r in latest.items()
                   if r.get("status") == logging_utils.STATUS_REQUIRES_HUMAN_LOGIN]
    failing = [s for s, r in latest.items() if r.get("status") == logging_utils.STATUS_FAILED]
    fine = [s for s, r in latest.items()
            if r.get("status") in (logging_utils.STATUS_SUCCESS,
                                   logging_utils.STATUS_SKIPPED)]

    print()
    if needs_login:
        print("  ACTION NEEDED: the portal session has expired.")
        print("  One headed run signs it back in:  ./scripts/run_once.sh")
        print("  Until then every report is stopped, uploading nothing.")
    elif failing:
        print(f"  ACTION NEEDED: {len(failing)} report(s) failing on the last run:")
        for slug in sorted(failing):
            print(f"      {slug:<{width}}  {latest[slug].get('error_category')}")
        if fine:
            print(f"  The other {len(fine)} are fine, so this is that report's "
                  f"own problem, not the session.")
    else:
        print(f"  All {len(fine)} report(s) are up to date.")

    print(f"\n  {len(records)} run record(s) in total. "
          f"One report's history:  --status --report <slug>\n")
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
    command.add_argument("--list-reports", action="store_true",
                         help="show every configured report")

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
    parser.add_argument("--report", default=None, metavar="SLUG",
                        help="run just this one report (default: every enabled "
                             "report)")
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
    if args.list_reports:
        return cmd_list_reports(args)
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
