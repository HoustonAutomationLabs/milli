"""Structured logging with redaction.

Two rules shape this module:

1. Nothing that could identify a child, a family or a worker may reach a log
   file or the console. The reports this tool moves carry names, dates of
   birth, SSNs and Medicaid numbers.
2. A log that hides *that something happened* is worse than useless. So the
   operational log records run outcomes in full — ids, timings, status,
   error category — and redacts only values.

Redaction is applied as a logging filter, so it covers every call site
including ones added later that forget to think about it.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

REDACTED = "[redacted]"

# Ordered most-specific first. Each pattern replaces the whole match.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Bearer tokens first: "Authorization: Bearer <token>" would otherwise be
    # matched by the key rule below, which consumes only the word "Bearer" and
    # leaves the token itself in the log.
    (re.compile(r"(?i)\b(?:authorization\s*[:=]\s*)?bearer\s+[A-Za-z0-9._\-]+"),
     "bearer " + REDACTED),
    # Credentials in any key=value or key: value shape.
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|username|user[_-]?id|"
                r"authorization|auth|cookie|session)\b\s*[:=]\s*\S+"),
     r"\1=" + REDACTED),
    # Direct identifiers.
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), REDACTED),                 # SSN
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), REDACTED),          # email
    (re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"),
     REDACTED),                                                       # phone
    (re.compile(r"(?<!\d)\d{9,}(?!\d)"), REDACTED),                   # long id runs
    # Dates of birth and any bare date — cheap, and DOB is the field that
    # matters most here.
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"), REDACTED),
    # Query strings can carry ids and filter values; keep the path only.
    (re.compile(r"(https?://[^\s?#]+)\?[^\s]*"), r"\1?" + REDACTED),
]

# Literal terms supplied by the operator (agency name, surnames, and so on).
_extra_terms: list[re.Pattern[str]] = []


def configure_extra_terms(terms: Iterable[str]) -> None:
    """Add operator-supplied literals to the scrubber."""
    global _extra_terms
    _extra_terms = [
        re.compile(re.escape(t.strip()), re.IGNORECASE)
        for t in terms
        if t and t.strip()
    ]


def redact(text: str) -> str:
    """Scrub a string. Safe to call on anything, including None-ish input."""
    if not text:
        return text
    out = str(text)
    for pattern, replacement in _PATTERNS:
        out = pattern.sub(replacement, out)
    for pattern in _extra_terms:
        out = pattern.sub(REDACTED, out)
    return out


def safe_url(url: Optional[str]) -> str:
    """A URL reduced to scheme, host and path. Query and fragment are dropped:
    report URLs carry filter values and record ids."""
    if not url:
        return ""
    return re.sub(r"[?#].*$", "", str(url))


def _redact_arg(value):
    """Redact strings; leave numbers and other types for the format spec."""
    if isinstance(value, str):
        return redact(value)
    return value


class RedactingFilter(logging.Filter):
    """Applies `redact` to the formatted message and to every argument."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            # Only strings are redacted. Coercing everything to str broke any
            # message using %d or %f: the number arrived as a string and the
            # whole log line failed to format, which loses the message
            # entirely -- the opposite of what a log is for.
            if isinstance(record.args, dict):
                record.args = {k: _redact_arg(v) for k, v in record.args.items()}
            else:
                record.args = tuple(_redact_arg(a) for a in record.args)
        # Tracebacks quote source lines and exception values, both of which can
        # carry page text. Keep the type, drop the rest.
        if record.exc_info:
            exc_type = record.exc_info[0]
            record.exc_text = f"{exc_type.__name__ if exc_type else 'Exception'} (detail suppressed)"
            record.exc_info = None
        return True


def get_logger(name: str = "er_sync", log_dir: Optional[Path] = None,
               verbose: bool = False) -> logging.Logger:
    """Console + optional file logger, both redacted."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler(stream=sys.stderr)
    console.setFormatter(fmt)
    console.addFilter(RedactingFilter())
    logger.addHandler(console)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / "er_sync.log"
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(fmt)
        handler.addFilter(RedactingFilter())
        logger.addHandler(handler)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    return logger


# ---------------------------------------------------------------------------
# Operational log
# ---------------------------------------------------------------------------

# The statuses a run may end in. Anything else is a bug.
STATUS_SUCCESS = "success"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
STATUS_REQUIRES_HUMAN_LOGIN = "requires_human_login"

ALL_STATUSES = (
    STATUS_SUCCESS,
    STATUS_SKIPPED,
    STATUS_FAILED,
    STATUS_REQUIRES_HUMAN_LOGIN,
)


@dataclass
class RunRecord:
    """One line of the operational log.

    Deliberately narrow. `error_category` is a fixed vocabulary, never an
    exception message: exception text from a browser routinely quotes page
    content, and page content here is case data.
    """

    run_id: str
    report_slug: str
    started_at: str
    ended_at: Optional[str] = None
    status: str = STATUS_FAILED
    error_category: Optional[str] = None
    local_filename: Optional[str] = None      # basename only, never full path
    drive_file_id: Optional[str] = None
    run_key: Optional[str] = None
    dry_run: bool = False
    notes: list[str] = field(default_factory=list)

    def finish(self, status: str, error_category: Optional[str] = None) -> "RunRecord":
        self.status = status
        self.error_category = error_category
        self.ended_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return self

    def note(self, text: str) -> None:
        self.notes.append(redact(text))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_run_record(log_dir: Path, record: RunRecord) -> Path:
    """Append the record to logs/runs.jsonl as one JSON object per line."""
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "runs.jsonl"
    line = json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(redact(line) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path
