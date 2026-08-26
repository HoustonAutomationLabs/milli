"""File validation, with the CSV header rules under the most scrutiny.

The cases that matter are the ones a size-only check would wave through: an
HTML error page saved with a report extension, and a CSV whose columns have
quietly changed.
"""

import csv

import pytest

from src.fixtures import build_fixture_set, write_sample_csv, write_sample_xlsx
from src.validators import (
    CATEGORY_BAD_EXTENSION,
    CATEGORY_CSV_HEADERS,
    CATEGORY_CSV_UNREADABLE,
    CATEGORY_MISSING_FILE,
    CATEGORY_TOO_SMALL,
    CATEGORY_XLSX_UNREADABLE,
    missing_headers,
    read_csv_header,
    validate_file,
)

HEADERS = ["Case #", "Task", "Due Date", "Status"]


@pytest.fixture()
def sample_csv(tmp_path):
    return write_sample_csv(tmp_path / "report.csv", HEADERS)


# -- the happy path ---------------------------------------------------------

def test_a_good_csv_passes_every_check(sample_csv):
    result = validate_file(sample_csv, min_bytes=100, expected_csv_headers=HEADERS)
    assert result.ok
    assert result.category is None
    assert "exists" in result.checks


def test_a_good_xlsx_opens(tmp_path):
    path = write_sample_xlsx(tmp_path / "report.xlsx", HEADERS)
    assert validate_file(path, min_bytes=100).ok


# -- the failures that matter ----------------------------------------------

def test_a_missing_file_is_reported_as_missing(tmp_path):
    result = validate_file(tmp_path / "nope.csv")
    assert not result.ok
    assert result.category == CATEGORY_MISSING_FILE


def test_a_short_file_fails_the_size_floor(sample_csv):
    result = validate_file(sample_csv, min_bytes=10_000_000)
    assert result.category == CATEGORY_TOO_SMALL


def test_an_html_error_page_named_xlsx_is_caught(tmp_path):
    """The failure mode a size check alone would miss: the portal served an
    'session expired' page and the browser saved it under the report name."""
    path = tmp_path / "report.xlsx"
    path.write_bytes(b"<html><body>Session expired</body></html>" + b" " * 4096)
    result = validate_file(path, min_bytes=100)
    assert result.category == CATEGORY_XLSX_UNREADABLE


def test_an_unapproved_extension_is_rejected(tmp_path):
    path = tmp_path / "report.exe"
    path.write_bytes(b"x" * 4096)
    result = validate_file(path, min_bytes=100)
    assert result.category == CATEGORY_BAD_EXTENSION


def test_an_extension_outside_the_allow_list_is_rejected(sample_csv):
    result = validate_file(sample_csv, min_bytes=100, allowed_extensions=["xlsx"])
    assert result.category == CATEGORY_BAD_EXTENSION


def test_configuring_an_extension_outside_the_approved_set_fails_closed(sample_csv):
    """Widening the allow-list in .env must not widen the approved set."""
    result = validate_file(sample_csv, min_bytes=100,
                           allowed_extensions=["csv", "exe"])
    assert result.category == CATEGORY_BAD_EXTENSION


def test_an_empty_csv_has_no_header_row(tmp_path):
    path = tmp_path / "report.csv"
    path.write_text("", encoding="utf-8")
    result = validate_file(path, min_bytes=0, expected_csv_headers=HEADERS)
    assert result.category == CATEGORY_CSV_UNREADABLE


# -- CSV headers ------------------------------------------------------------

def test_a_renamed_column_fails_validation(tmp_path):
    path = write_sample_csv(tmp_path / "report.csv",
                            ["Case #", "Task", "Due Date", "State"])
    result = validate_file(path, min_bytes=100, expected_csv_headers=HEADERS)
    assert result.category == CATEGORY_CSV_HEADERS
    assert "Status" in result.detail


def test_extra_columns_are_allowed(tmp_path):
    """Reports gain columns over time; that must not fail a run."""
    path = write_sample_csv(tmp_path / "report.csv", HEADERS + ["New Column"])
    assert validate_file(path, min_bytes=100, expected_csv_headers=HEADERS).ok


def test_header_matching_ignores_case_and_surrounding_whitespace():
    assert missing_headers(["  case # ", "STATUS"], ["Case #", "Status"]) == []


def test_missing_headers_lists_only_what_is_absent():
    assert missing_headers(["Case #"], ["Case #", "Status", "Task"]) == \
        ["Status", "Task"]


def test_no_expected_headers_means_the_header_check_is_skipped(tmp_path):
    path = write_sample_csv(tmp_path / "report.csv", ["Anything"])
    assert validate_file(path, min_bytes=100, expected_csv_headers=[]).ok


# -- encodings --------------------------------------------------------------

def test_a_windows_1252_csv_is_readable(tmp_path):
    """ExtendedReach's Compliance export is cp1252, not UTF-8. A single-encoding
    reader would fail on a perfectly valid file."""
    path = tmp_path / "report.csv"
    with path.open("w", encoding="cp1252", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Case #", "Notes"])
        writer.writerow(["C-1", "temperature 21° — fine"])
    assert read_csv_header(path, ("utf-8", "cp1252")) == ["Case #", "Notes"]


def test_a_utf8_bom_is_stripped_from_the_first_header(tmp_path):
    path = tmp_path / "report.csv"
    path.write_text("Case #,Status\nC-1,Open\n", encoding="utf-8-sig")
    assert read_csv_header(path)[0] == "Case #"


def test_quoted_headers_containing_commas_parse_as_one_column(tmp_path):
    path = tmp_path / "report.csv"
    path.write_text('"Last, First",Status\n"Doe, J",Open\n', encoding="utf-8")
    assert read_csv_header(path) == ["Last, First", "Status"]


# -- the fixture set as a whole --------------------------------------------

def test_the_generated_fixture_set_behaves_as_documented(tmp_path):
    expected_failures = {"sample_truncated.csv", "sample_error_page.xlsx"}
    for path in build_fixture_set(tmp_path, HEADERS):
        result = validate_file(path, min_bytes=1024, expected_csv_headers=HEADERS)
        assert result.ok is (path.name not in expected_failures), path.name


def test_validation_detail_never_echoes_file_contents(tmp_path):
    """A validator that quoted the offending row into its message would put
    case data into the log this project spends so much effort redacting."""
    path = write_sample_csv(tmp_path / "report.csv", ["Case #", "Secret Value"])
    result = validate_file(path, min_bytes=100, expected_csv_headers=HEADERS)
    assert not result.ok
    assert "Secret Value" not in result.detail
    assert "CASE-0001" not in result.detail
