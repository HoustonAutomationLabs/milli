#!/bin/bash
#
# Double-click this file to install everything.
#
# A .command file is a script macOS will run when you double-click it, in a
# Terminal window it opens for you. That is the only reason this exists: so
# the first step needs no typing at all.
#
# IF DOUBLE-CLICKING IS BLOCKED: macOS refuses to launch files downloaded from
# the internet unless they are signed by a registered developer, and on recent
# versions the right-click-and-Open bypass is gone -- the dialog has only an OK
# button. Run it from Terminal instead, which is not subject to that check:
#
#     type:  bash        (with a trailing space)
#     then:  drag this file into the Terminal window
#     then:  press Return
#
# See INSTALL.txt.

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

# Look on PATH first, then in the places the python.org installer and Homebrew
# put things. A Terminal window opened BEFORE Python was installed still has the
# old PATH, so searching those directories directly saves the user from an error
# that looks identical to not having installed it at all.
PY=""
FOUND_BUT_OLD=""
CANDIDATES="python3.14 python3.13 python3.12 python3.11 python3"
for dir in /Library/Frameworks/Python.framework/Versions/*/bin \
           /opt/homebrew/bin /usr/local/bin; do
  for v in 3.14 3.13 3.12 3.11; do
    [ -x "$dir/python$v" ] && CANDIDATES="$CANDIDATES $dir/python$v"
  done
  [ -x "$dir/python3" ] && CANDIDATES="$CANDIDATES $dir/python3"
done

for candidate in $CANDIDATES; do
  path="$candidate"
  case "$candidate" in
    /*) [ -x "$path" ] || continue ;;
    *)  command -v "$candidate" >/dev/null 2>&1 || continue
        path="$(command -v "$candidate")" ;;
  esac
  if "$path" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
    PY="$path"; break
  fi
  # Remember the newest too-old one, so the message can say what is there.
  ver="$("$path" --version 2>&1)"
  [ -z "$FOUND_BUT_OLD" ] && FOUND_BUT_OLD="$ver"
done

if [ -z "$PY" ]; then
  echo
  if [ -n "$FOUND_BUT_OLD" ]; then
    echo "${RED}Found $FOUND_BUT_OLD, but this needs Python 3.11 or newer.${OFF}"
    echo "${DIM}That older one came with macOS. Installing a newer Python does not${OFF}"
    echo "${DIM}remove it or affect anything else on your Mac.${OFF}"
  else
    echo "${RED}No Python was found on this Mac.${OFF}"
  fi
  echo
  echo "  ${BOLD}1.${OFF} Go to  ${BOLD}https://www.python.org/downloads/macos/${OFF}"
  echo "  ${BOLD}2.${OFF} Download the latest ${BOLD}macOS 64-bit universal2 installer${OFF}"
  echo "  ${BOLD}3.${OFF} Open it and click through, accepting every default"
  echo
  echo "  ${BOLD}4.${OFF} ${BOLD}Close this Terminal window completely${OFF} and open a new one."
  echo "     ${DIM}This matters: a window opened before the install cannot see it.${OFF}"
  echo
  echo "  ${BOLD}5.${OFF} Run this installer again — type  ${BOLD}bash${OFF}  and a space,"
  echo "     drag this file into the window, press Return."
  echo
  echo "Press Return to close this window."
  read -r _
  exit 1
fi
echo "      ${GREEN}found $("$PY" --version) at $PY${OFF}"

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
echo "${DIM}To run this again later: in Terminal, type  bash  then drag this${OFF}"
echo "${DIM}file in and press Return. It is safe to re-run and skips what is done.${OFF}"
echo
echo "Press Return to close this window."
read -r _
