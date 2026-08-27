"""Redaction.

Not in the required test list, but redaction is the control standing between
this tool's logs and a PHI disclosure. An untested control is an assumption.
"""

import json

from src import logging_utils
from src.logging_utils import (
    REDACTED,
    RunRecord,
    configure_extra_terms,
    redact,
    safe_url,
    write_run_record,
)


def test_a_password_in_any_shape_is_scrubbed():
    for text in ("password=hunter2", "password: hunter2", "PASSWORD = hunter2"):
        assert "hunter2" not in redact(text)


def test_tokens_and_bearer_headers_are_scrubbed():
    assert "ya29" not in redact("Authorization: Bearer ya29.A0ARrdaM-secret")
    assert "abc123" not in redact("token=abc123")


def test_direct_identifiers_are_scrubbed():
    text = redact("ssn 123-45-6789, dob 4/12/2015, mail a.b@example.org, "
                  "phone 713-555-0199, medicaid 123456789012")
    for leak in ("123-45-6789", "4/12/2015", "a.b@example.org",
                 "713-555-0199", "123456789012"):
        assert leak not in text
    assert REDACTED in text


def test_a_query_string_is_dropped_from_a_url():
    """Report URLs carry filter values and record ids."""
    assert safe_url("https://x.example/report?case=1234&worker=Jane") == \
        "https://x.example/report"


def test_operator_supplied_terms_are_scrubbed():
    configure_extra_terms(["Rivera", "Houston Strong CPA"])
    try:
        assert "Rivera" not in redact("worker rivera closed the task")
        assert "Houston Strong CPA" not in redact("Houston Strong CPA export")
    finally:
        configure_extra_terms([])


def test_redaction_survives_empty_and_none_input():
    assert redact("") == ""
    assert redact(None) is None


def test_the_run_record_written_to_disk_is_redacted(tmp_path):
    record = RunRecord(run_id="r1", report_slug="pastdue_case",
                       started_at="2026-08-26T18:00:00+00:00")
    record.note("failed for case of client a.b@example.org ssn 123-45-6789")
    record.finish(logging_utils.STATUS_FAILED, "csv_headers_missing")

    path = write_run_record(tmp_path, record)
    written = path.read_text(encoding="utf-8")

    assert "a.b@example.org" not in written
    assert "123-45-6789" not in written
    # The outcome itself must survive: a log that hides the failure is useless.
    parsed = json.loads(written.strip())
    assert parsed["status"] == "failed"
    assert parsed["error_category"] == "csv_headers_missing"
    assert parsed["run_id"] == "r1"


def test_run_records_append_one_json_object_per_line(tmp_path):
    for index in range(3):
        write_run_record(tmp_path, RunRecord(
            run_id=f"r{index}", report_slug="s", started_at="t"))
    lines = (tmp_path / "runs.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3
    assert [json.loads(line)["run_id"] for line in lines] == ["r0", "r1", "r2"]


def test_the_run_log_file_is_not_world_readable(tmp_path):
    path = write_run_record(tmp_path, RunRecord(
        run_id="r", report_slug="s", started_at="t"))
    assert path.stat().st_mode & 0o077 == 0


def test_every_status_used_by_the_cli_is_declared():
    assert set(logging_utils.ALL_STATUSES) == {
        "success", "skipped", "failed", "requires_human_login"}


def test_numeric_arguments_survive_redaction(caplog):
    """Coercing every argument to a string broke %d formatting, which loses the
    whole message -- the opposite of what a log is for."""
    import logging

    logger = logging.getLogger("redact_numeric_test")
    logger.handlers.clear()
    logger.addFilter(logging_utils.RedactingFilter())
    logger.setLevel(logging.INFO)
    with caplog.at_level(logging.INFO, logger="redact_numeric_test"):
        logger.info("Run %s starting: %d report(s)", "abc123", 9)
    assert "9 report(s)" in caplog.text


def test_string_arguments_are_still_redacted(caplog):
    import logging

    logger = logging.getLogger("redact_string_test")
    logger.handlers.clear()
    logger.addFilter(logging_utils.RedactingFilter())
    logger.setLevel(logging.INFO)
    with caplog.at_level(logging.INFO, logger="redact_string_test"):
        logger.info("contact %s", "a.b@example.org")
    assert "a.b@example.org" not in caplog.text
    assert REDACTED in caplog.text
