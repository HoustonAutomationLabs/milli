"""Synthetic sample files for offline testing.

These are generated, never committed. Two reasons:

1. A committed sample of an ExtendedReach export would be case data, and this
   repository's rules put that permanently out of bounds.
2. The repository root .gitignore excludes *.csv and *.xlsx outright, so a
   committed fixture would silently not exist for anyone who cloned. Generating
   them removes that trap entirely.

Every value here is invented. The names are placeholders in the literal sense:
no real person's data is used to test a tool that moves real people's data.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

# Deliberately bland, obviously fake, and never derived from a real export.
_SAMPLE_ROWS = [
    ["CASE-0001", "Sample Task A", "2026-01-15", "In Process"],
    ["CASE-0002", "Sample Task B", "2026-02-01", "Submitted"],
    ["CASE-0003", "Sample Task C", "2026-03-12", "In Process"],
]


def write_sample_csv(path: Path, headers: Sequence[str],
                     rows: int = 40, encoding: str = "utf-8") -> Path:
    """A CSV with the given headers, padded to clear a minimum-size check."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(headers))
        for index in range(rows):
            template = _SAMPLE_ROWS[index % len(_SAMPLE_ROWS)]
            row = [f"{template[0]}-{index:03d}"] + template[1:]
            # Pad or trim to the header width.
            row = (row + [f"value_{index}"] * len(headers))[:len(headers)]
            writer.writerow(row)
    return path


def write_sample_xlsx(path: Path, headers: Sequence[str], rows: int = 40) -> Path:
    from openpyxl import Workbook

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sample"
    sheet.append(list(headers))
    for index in range(rows):
        sheet.append([f"value_{index}_{column}" for column in range(len(headers))])
    workbook.save(path)
    return path


def write_sample_pdf(path: Path) -> Path:
    """A minimal but structurally valid single-page PDF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        b"trailer<</Root 1 0 R>>\n"
        b"%%EOF\n"
    )
    path.write_bytes(body + b"% padding\n" * 200)
    return path


def build_fixture_set(directory: Path, headers: Sequence[str]) -> list[Path]:
    """One sample per supported format, plus the failure cases worth testing."""
    directory.mkdir(parents=True, exist_ok=True)
    created = [
        write_sample_csv(directory / "sample_report.csv", headers),
        # ExtendedReach's Compliance export is Windows-1252, so cover it.
        write_sample_csv(directory / "sample_report_cp1252.csv", headers,
                         encoding="cp1252"),
        write_sample_xlsx(directory / "sample_report.xlsx", headers),
        write_sample_pdf(directory / "sample_report.pdf"),
    ]

    # A truncated file: what a failed export actually looks like on disk.
    (directory / "sample_truncated.csv").write_text("a,b\n", encoding="utf-8")
    created.append(directory / "sample_truncated.csv")

    # An HTML error page saved under a report extension — the failure mode
    # that a size-only check would wave through.
    (directory / "sample_error_page.xlsx").write_bytes(
        b"<html><body>Session expired</body></html>" + b" " * 2048)
    created.append(directory / "sample_error_page.xlsx")

    return created
