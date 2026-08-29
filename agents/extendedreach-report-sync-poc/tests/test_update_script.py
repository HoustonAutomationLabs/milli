"""Guards on UPDATE.command.

The script replaces its own file while running. Bash reads a script
incrementally, so the first version died on a syntax error part-way through:
it resumed parsing the *new* file at the old byte offset. Wrapping the body in
a function forces bash to parse all of it before running any of it.

These are static checks — the script's real behaviour was verified by running
it against a stale install with settings, twice.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "UPDATE.command"


@pytest.fixture(scope="module")
def text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_the_script_exists_and_parses():
    result = subprocess.run(["bash", "-n", str(SCRIPT)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_the_body_is_wrapped_so_it_cannot_overwrite_itself_mid_run(text):
    """The specific bug: a script that replaces its own file while bash is
    still reading it."""
    assert "update_main() {" in text
    assert re.search(r'^update_main "\$@"$', text, re.MULTILINE)

    # The copy that overwrites the project must be inside the function, not
    # at top level where it would run before the whole file was parsed.
    body = text[text.index("update_main() {"):]
    assert 'cp -R "$NEW/."' in body


def test_settings_are_saved_aside_rather_than_excluded(text):
    """Relying on an exclude list means one mistake destroys a configuration
    that took an evening to enter. Copy them out, copy them back."""
    for kept in (".env", "config/workflow.json"):
        assert f'"$KEEP/{kept}"' in text or f'{kept} "$KEEP' in text
    assert 'cp "$KEEP/.env" .env' in text


def test_the_download_is_verified_before_anything_is_overwritten(text):
    """A truncated download must never replace a working install."""
    verify = text.index("tar -tzf")
    overwrite = text.index('cp -R "$NEW/."')
    assert verify < overwrite


def test_it_refuses_to_run_outside_an_install(text):
    """So a mistaken drag cannot unpack the project over an unrelated folder."""
    assert "src/main.py" in text
    guard = text.index("[ -f src/main.py ]")
    assert guard < text.index("curl")


def test_it_targets_the_public_repository(text):
    assert "HoustonAutomationLabs/milli" in text
    assert "codeload.github.com" in text
