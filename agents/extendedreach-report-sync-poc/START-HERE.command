#!/bin/bash
#
# Double-click this file to install everything.
#
# A .command file is a script macOS will run when you double-click it, in a
# Terminal window it opens for you. That is the only reason this exists: so
# the first step needs no typing at all.

# Run from this file's own folder, wherever the user put it.
cd "$(dirname "$0")" || exit 1

BOLD=$'\033[1m'; GREEN=$'\033[32m'; RED=$'\033[31m'; DIM=$'\033[2m'; OFF=$'\033[0m'

echo
echo "${BOLD}ExtendedReach Report Sync — installer${OFF}"
echo "${DIM}Installing into: $(pwd)${OFF}"
echo
echo "This takes about 10 minutes, mostly downloading a browser."
echo "You can leave it running. Nothing here touches ExtendedReach."
echo

fail() {
  echo
  echo "${RED}${BOLD}Stopped: $1${OFF}"
  echo
  echo "Copy everything above and send it to Claude — the message says what to do."
  echo
  echo "Press Return to close this window."
  read -r _
  exit 1
}

# ---------------------------------------------------------------- Python
echo "${BOLD}[1/4]${OFF} Checking Python..."
PY=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
      PY="$candidate"; break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo
  echo "${RED}Python 3.11 or newer is not installed.${OFF}"
  echo
  echo "Install it once, then double-click this file again:"
  echo "  1. Go to  ${BOLD}python.org/downloads${OFF}"
  echo "  2. Download the macOS installer and run it"
  echo "  3. Accept the defaults"
  echo
  echo "Press Return to close this window."
  read -r _
  exit 1
fi
echo "      ${GREEN}found $($PY --version)${OFF}"

# ---------------------------------------------------------------- venv
echo "${BOLD}[2/4]${OFF} Setting up a private workspace for this tool..."
if [ ! -d .venv ]; then
  "$PY" -m venv .venv || fail "could not create the workspace folder (.venv)"
fi
./.venv/bin/pip install --upgrade pip >/dev/null 2>&1
./.venv/bin/pip install -r requirements.txt >/dev/null 2>&1 \
  || fail "could not download the required components. Check your internet connection."
echo "      ${GREEN}done${OFF}"

# ---------------------------------------------------------------- browser
echo "${BOLD}[3/4]${OFF} Downloading the browser it drives (the slow part)..."
./.venv/bin/playwright install chromium >/dev/null 2>&1 \
  || fail "could not download Chromium. Check your internet connection and try again."
echo "      ${GREEN}done${OFF}"

# ---------------------------------------------------------------- self-test
echo "${BOLD}[4/4]${OFF} Testing that everything works..."
if ./.venv/bin/python -m pytest -q >/tmp/er-sync-tests.txt 2>&1; then
  echo "      ${GREEN}$(grep -oE '[0-9]+ passed' /tmp/er-sync-tests.txt | tail -1) — all good${OFF}"
else
  tail -20 /tmp/er-sync-tests.txt
  fail "the self-test did not pass"
fi

# ---------------------------------------------------------------- done
echo
echo "${GREEN}${BOLD}Installed successfully.${OFF}"
echo
echo "Nothing is connected to ExtendedReach or Google yet — that is the next part,"
echo "and it needs you. Here is where you stand:"
echo
./.venv/bin/python -m src.main --doctor
echo
echo "${DIM}To come back here later, double-click this same file — it is safe to${OFF}"
echo "${DIM}run again and will skip anything already done.${OFF}"
echo
echo "Press Return to close this window."
read -r _
