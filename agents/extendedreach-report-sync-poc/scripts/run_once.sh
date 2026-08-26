#!/usr/bin/env bash
#
# One export. Safe to call from launchd.
#
# Any argument is passed through, so this works too:
#   ./scripts/run_once.sh --dry-run
#   ./scripts/run_once.sh --headless
#
# Exit codes (a scheduler can alert on these):
#   0  success, or a duplicate that was correctly skipped
#   1  unexpected error
#   2  configuration invalid
#   3  a person must complete sign-in       <- re-run headed
#   4  the downloaded file failed validation
#   5  navigation or download failed
#   6  Google Drive upload failed
#   7  another run is already in progress

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -x ./.venv/bin/python ]; then
  echo "No virtual environment. Run ./scripts/install_playwright.sh first." >&2
  exit 2
fi

# launchd starts jobs with a near-empty environment; .env is loaded by the
# application itself, so nothing sensitive needs to be exported here.
exec ./.venv/bin/python -m src.main --once "$@"
