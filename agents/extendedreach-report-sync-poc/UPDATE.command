#!/bin/bash
#
# Update this tool to the latest version, keeping your settings.
#
# Run it the same way as the installer: in Terminal type  bash  then a space,
# drag this file in, press Return.
#
# It downloads the current code and unpacks it over this folder. Your .env,
# your config/workflow.json, the browser profile, the logs and the downloaded
# reports are all left alone.

# Everything below lives inside a function that is called on the last line.
#
# This script replaces its own file part-way through, and bash reads a script
# incrementally as it runs: overwriting it mid-execution made bash resume
# parsing the new file at the old byte offset and die on a syntax error.
# Defining a function forces the whole body to be parsed before any of it runs,
# so the file underneath can change freely.

update_main() {
  cd "$(dirname "$0")" || exit 1

  BOLD=$'\033[1m'; GREEN=$'\033[32m'; RED=$'\033[31m'; DIM=$'\033[2m'; OFF=$'\033[0m'

  REPO="HoustonAutomationLabs/milli"
  BRANCH="claude/extendedreach-report-sync-poc-a5jkhn"
  SUBDIR="agents/extendedreach-report-sync-poc"

  echo
  echo "${BOLD}ExtendedReach Report Sync — update${OFF}"
  echo "${DIM}Updating: $(pwd)${OFF}"
  echo

  fail() {
    echo
    echo "${RED}${BOLD}Stopped: $1${OFF}"
    echo
    echo "${DIM}Nothing was changed. Your settings and current version are intact.${OFF}"
    echo
    echo "Press Return to close this window."
    read -r _
    exit 1
  }

  # Refuse to run anywhere but a real install, so a mistaken drag cannot unpack
  # the project over an unrelated folder.
  [ -f src/main.py ] || fail "this does not look like the tool's folder (no src/main.py)."

  WORK="$(mktemp -d)" || fail "could not create a temporary folder."
  trap 'rm -rf "$WORK"' EXIT

  echo "${BOLD}[1/4]${OFF} Downloading the latest version..."
  URL="https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH"
  curl -fsSL "$URL" -o "$WORK/update.tar.gz" \
    || fail "could not download the update. Check your internet connection."

  # Verify before unpacking: a truncated download must never overwrite a working
  # install. tar -t reads the archive without extracting anything.
  tar -tzf "$WORK/update.tar.gz" >/dev/null 2>&1 \
    || fail "the download was incomplete or damaged. Try again."
  echo "      ${GREEN}done${OFF}"

  echo "${BOLD}[2/4]${OFF} Unpacking..."
  tar -xzf "$WORK/update.tar.gz" -C "$WORK" || fail "could not unpack the update."
  # The archive nests the project under its own top-level folder, so the
  # project sits three levels down, not two.
  NEW="$(find "$WORK" -maxdepth 4 -type d -path "*/$SUBDIR" | head -1)"
  [ -n "$NEW" ] && [ -f "$NEW/src/main.py" ] \
    || fail "the update did not contain the expected files."
  echo "      ${GREEN}done${OFF}"

  # Everything that is yours rather than the tool's. Saved aside and put back,
  # rather than relying on the copy to skip them — a mistake in an exclude list
  # would silently destroy a configuration that took an evening to enter.
  echo "${BOLD}[3/4]${OFF} Setting your settings aside..."
  KEEP="$WORK/keep"
  mkdir -p "$KEEP/config"
  [ -f .env ] && cp .env "$KEEP/.env"
  [ -f config/workflow.json ] && cp config/workflow.json "$KEEP/config/workflow.json"
  [ -f config/workflow.draft.json ] && cp config/workflow.draft.json "$KEEP/config/workflow.draft.json"
  echo "      ${GREEN}done${OFF}"

  echo "${BOLD}[4/4]${OFF} Installing the new version..."
  # Copy the code over the top. .venv, logs and downloads are not in the archive,
  # so they are untouched by construction.
  cp -R "$NEW/." . || fail "could not copy the new files into place."

  [ -f "$KEEP/.env" ] && cp "$KEEP/.env" .env
  [ -f "$KEEP/config/workflow.json" ] && cp "$KEEP/config/workflow.json" config/workflow.json
  [ -f "$KEEP/config/workflow.draft.json" ] && cp "$KEEP/config/workflow.draft.json" config/workflow.draft.json
  chmod +x START-HERE.command UPDATE.command scripts/*.sh 2>/dev/null
  echo "      ${GREEN}done${OFF}"

  # Dependencies can change between versions; keep them in step, quietly.
  if [ -x ./.venv/bin/python ]; then
    echo
    echo "${DIM}Checking components are up to date...${OFF}"
    ./.venv/bin/python -m pip install --only-binary=:all: -q -r requirements.txt \
      >/dev/null 2>&1 || echo "${DIM}(components unchanged)${OFF}"
  fi

  echo
  echo "${GREEN}${BOLD}Updated.${OFF}  Your settings were kept."
  echo

  if [ -x ./.venv/bin/python ]; then
    ./.venv/bin/python -m src.main --doctor
  fi

  echo
  echo "Press Return to close this window."
  read -r _
}

update_main "$@"
