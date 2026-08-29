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

LOG="$(pwd)/install-log.txt"

fail() {
  echo
  echo "${RED}${BOLD}Stopped: $1${OFF}"
  if [ -s "$LOG" ]; then
    echo
    echo "${BOLD}The actual error was:${OFF}"
    echo "${DIM}------------------------------------------------------------${OFF}"
    tail -18 "$LOG"
    echo "${DIM}------------------------------------------------------------${OFF}"
    echo
    echo "Full details saved to: ${BOLD}install-log.txt${OFF} (next to this file)"
  fi
  echo
  echo "Copy everything above and send it to Claude."
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
CANDIDATES="python3.13 python3.12 python3.11 python3.14 python3.15 python3"
for dir in /Library/Frameworks/Python.framework/Versions/*/bin \
           /opt/homebrew/bin /usr/local/bin; do
  for v in 3.13 3.12 3.11 3.14 3.15; do
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

# Some Python installations arrive without pip, the part that downloads
# packages. The python.org installer's own "Install Certificates" step fails
# the same way ("No module named pip"). Left alone, venv then produces an
# environment with no pip and every later step fails with a message that
# blames the network. ensurepip ships inside Python and restores it.
if ! "$PY" -m pip --version >/dev/null 2>&1; then
  echo "      ${DIM}this Python is missing pip — repairing it${OFF}"
  : > "$LOG"
  "$PY" -m ensurepip --upgrade >>"$LOG" 2>&1 \
    || fail "this Python installation is incomplete and could not be repaired. Re-run the installer from python.org, letting it finish completely."
fi

if [ ! -d .venv ]; then
  : > "$LOG"
  "$PY" -m venv .venv >>"$LOG" 2>&1 || fail "could not create the workspace folder (.venv)"
fi

# Same check inside the workspace: a venv built by a pip-less Python has none.
if ! ./.venv/bin/python -m pip --version >/dev/null 2>&1; then
  echo "      ${DIM}repairing the workspace${OFF}"
  : > "$LOG"
  ./.venv/bin/python -m ensurepip --upgrade >>"$LOG" 2>&1 \
    || fail "the workspace has no package installer and could not be repaired."
fi
./.venv/bin/python -m pip install --upgrade pip >"$LOG" 2>&1
# Truncate before the step that matters, so the error shown on failure is that
# step's own output and not the tail of a successful one.
: > "$LOG"
./.venv/bin/python -m pip install -r requirements.txt >>"$LOG" 2>&1 \
  || fail "could not install the required components."
echo "      ${GREEN}done${OFF}"

# ---------------------------------------------------------------- browser
echo "${BOLD}[3/4]${OFF} Downloading the browser it drives (the slow part)..."
: > "$LOG"
./.venv/bin/python -m playwright install chromium >>"$LOG" 2>&1 \
  || fail "could not download Chromium."
echo "      ${GREEN}done${OFF}"

# ---------------------------------------------------------------- self-test
echo "${BOLD}[4/4]${OFF} Testing that everything works..."
if ./.venv/bin/python -m pytest >/tmp/er-sync-tests.txt 2>&1; then
  passed="$(grep -oE '[0-9]+ passed' /tmp/er-sync-tests.txt | tail -1)"
  echo "      ${GREEN}${passed:-all checks} — all good${OFF}"
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
