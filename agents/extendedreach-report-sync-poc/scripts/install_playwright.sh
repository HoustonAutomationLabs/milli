#!/usr/bin/env bash
#
# One-time setup: virtual environment, Python dependencies, Chromium.
# macOS. Run from the project directory.

set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"

echo "==> Checking Python version"
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    sys.exit(f"Python 3.11+ required, found {sys.version.split()[0]}")
print(f"    Python {sys.version.split()[0]}")
PY

echo "==> Creating the virtual environment (.venv)"
[ -d .venv ] || "$PYTHON" -m venv .venv

echo "==> Installing Python dependencies"
./.venv/bin/pip install --upgrade pip >/dev/null
./.venv/bin/pip install -r requirements.txt

echo "==> Installing the Chromium build Playwright expects"
# Chromium only. This tool drives one browser and has no reason to download
# Firefox and WebKit as well.
./.venv/bin/playwright install chromium

echo "==> Running the offline test suite"
./.venv/bin/python -m pytest

cat <<'NEXT'

Setup complete.

Next:
  1. cp .env.example .env                        and fill in every TODO
  2. cp config/workflow.example.json config/workflow.json
                                                 and fill in every TODO
  3. ./.venv/bin/python -m src.main --validate-config
  4. ./scripts/run_once.sh --dry-run             first headed run, no upload

Nothing will work against the live portal until the report URL, the
selectors and an authorised account are supplied. That is expected.
NEXT
