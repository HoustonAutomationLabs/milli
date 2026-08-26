"""Filename and run-key generation.

The filename convention is a contract: the duplicate check derives its
filename prefix from the same slug and date, so a change to one of these
functions that is not mirrored in the other silently re-uploads every day.
"""

from datetime import datetime

import pytest

from src.validators import (
    build_filename,
    build_run_key,
    filename_prefix_for_run_key,
    normalise_extension,
    slugify,
)

WHEN = datetime(2026, 8, 26, 18, 5, 3)


def test_filename_matches_the_required_convention():
    assert build_filename("pastdue_case", "csv", WHEN) == \
        "extendedreach_pastdue_case_2026-08-26_180503.csv"


def test_filename_pads_single_digit_time_components():
    assert build_filename("r", "csv", datetime(2026, 1, 2, 3, 4, 5)) == \
        "extendedreach_r_2026-01-02_030405.csv"


@pytest.mark.parametrize("raw,expected", [
    ("Past Due Case Tasks", "past_due_case_tasks"),
    ("  Mixed Case  ", "mixed_case"),
    ("weird//chars!!", "weird_chars"),
    ("Case #", "case"),
    ("", "report"),
])
def test_slugify_produces_filesystem_safe_slugs(raw, expected):
    assert slugify(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("csv", "csv"), (".CSV", "csv"), ("  .XlsX ", "xlsx"), ("", ""),
])
def test_extension_normalisation(raw, expected):
    assert normalise_extension(raw) == expected


def test_a_slug_cannot_escape_the_download_directory():
    # A slug is interpolated into a path, so traversal must not survive it.
    name = build_filename("../../etc/passwd", "csv", WHEN)
    assert "/" not in name and ".." not in name


def test_run_key_is_stable_across_a_day_but_changes_between_days():
    morning = build_run_key("pastdue_case", datetime(2026, 8, 26, 6, 0, 0))
    evening = build_run_key("pastdue_case", datetime(2026, 8, 26, 23, 59, 59))
    tomorrow = build_run_key("pastdue_case", datetime(2026, 8, 27, 6, 0, 0))
    assert morning == evening
    assert morning != tomorrow


def test_run_key_differs_between_reports():
    assert build_run_key("a", WHEN) != build_run_key("b", WHEN)


def test_filename_prefix_matches_the_filename_for_the_same_run():
    """The duplicate check depends on this exact relationship."""
    prefix = filename_prefix_for_run_key("pastdue_case", WHEN)
    filename = build_filename("pastdue_case", "csv", WHEN)
    assert filename.startswith(prefix)


def test_filename_prefix_matches_any_time_on_the_same_day():
    prefix = filename_prefix_for_run_key("pastdue_case", datetime(2026, 8, 26, 6, 0))
    later = build_filename("pastdue_case", "csv", datetime(2026, 8, 26, 22, 30))
    assert later.startswith(prefix)
