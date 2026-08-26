#!/usr/bin/env bash
#
# Install (or remove) the macOS launchd schedule for this job.
#
#   ./scripts/install_schedule.sh daily            6:00 PM every day
#   ./scripts/install_schedule.sh business-hours   8,10,12,2,4,6 on weekdays
#   ./scripts/install_schedule.sh --uninstall      remove whichever is loaded
#   ./scripts/install_schedule.sh daily --force    skip the safety check
#
# It writes the .plist with your real paths filled in, loads it, and shows
# you how to check on it. No XML editing.

set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd -P)"

LABEL="com.agency.extendedreach-report-sync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

MODE=""
FORCE="no"
for arg in "$@"; do
  case "$arg" in
    daily|business-hours) MODE="$arg" ;;
    --uninstall)          MODE="uninstall" ;;
    --force)              FORCE="yes" ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

if [ -z "$MODE" ]; then
  echo "Usage: $0 {daily|business-hours|--uninstall} [--force]" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

if [ "$MODE" = "uninstall" ]; then
  if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Removed the schedule. The job will no longer run on its own."
    echo "Nothing else was deleted — your downloads, logs and Drive files stay."
  else
    echo "No schedule was installed."
  fi
  exit 0
fi

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

if [ "$(uname -s)" != "Darwin" ]; then
  echo "launchd is macOS-only. On Linux use systemd or cron instead." >&2
  exit 2
fi

if [ ! -x ./.venv/bin/python ]; then
  echo "No virtual environment. Run ./scripts/install_playwright.sh first." >&2
  exit 2
fi

echo "==> Checking the configuration"
if ! ./.venv/bin/python -m src.main --validate-config >/dev/null 2>&1; then
  echo >&2
  echo "Configuration is not complete yet. Scheduling it now would just" >&2
  echo "produce a failure every evening. Run this to see what is missing:" >&2
  echo >&2
  echo "  ./.venv/bin/python -m src.main --validate-config" >&2
  exit 2
fi

# The point of the schedule is to repeat something that already works. If it
# has never worked once by hand, a timer only automates the failure.
LOG_DIR="$(./.venv/bin/python -c 'import sys; sys.path.insert(0,"."); from src import config; print(config.load().log_dir)')"
if [ "$FORCE" != "yes" ]; then
  if ! grep -q '"status": "success"' "$LOG_DIR/runs.jsonl" 2>/dev/null; then
    echo >&2
    echo "This job has never completed successfully by hand." >&2
    echo >&2
    echo "Do one real run first, so the browser profile holds a signed-in" >&2
    echo "session and you can see the file land in Drive:" >&2
    echo >&2
    echo "  ./scripts/run_once.sh" >&2
    echo >&2
    echo "Then run this again. (--force skips this check.)" >&2
    exit 2
  fi
fi

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

# ---------------------------------------------------------------------------
# Build the schedule block
# ---------------------------------------------------------------------------

if [ "$MODE" = "daily" ]; then
  SCHEDULE="    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>18</integer>
        <key>Minute</key><integer>0</integer>
    </dict>"
  THROTTLE=300
  DESCRIPTION="6:00 PM every day"
else
  # Weekday 1-5 is Monday-Friday. Listing every hour is verbose but fires at
  # exact times instead of drifting from whenever the job was last loaded.
  SCHEDULE="    <key>StartCalendarInterval</key>
    <array>"
  for day in 1 2 3 4 5; do
    for hour in 8 10 12 14 16 18; do
      SCHEDULE="$SCHEDULE
        <dict><key>Weekday</key><integer>$day</integer><key>Hour</key><integer>$hour</integer><key>Minute</key><integer>0</integer></dict>"
    done
  done
  SCHEDULE="$SCHEDULE
    </array>"
  # Longer than a normal run, so an overrun cannot be relaunched on top of
  # itself. The file lock in main.py is the real guard; this is belt and braces.
  THROTTLE=1200
  DESCRIPTION="8am, 10am, 12pm, 2pm, 4pm and 6pm, Monday to Friday"
fi

# ---------------------------------------------------------------------------
# Write and load
# ---------------------------------------------------------------------------

echo "==> Writing $PLIST"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/scripts/run_once.sh</string>
        <string>--headless</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

$SCHEDULE

    <!-- Never restart on its own. A failure here means a person should look. -->
    <key>KeepAlive</key>
    <false/>
    <key>RunAtLoad</key>
    <false/>
    <key>ThrottleInterval</key>
    <integer>$THROTTLE</integer>

    <key>StandardOutPath</key>
    <string>$LOG_DIR/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/launchd.err.log</string>
</dict>
</plist>
PLIST_EOF

plutil -lint "$PLIST" >/dev/null

echo "==> Loading it"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

cat <<DONE

Scheduled: $DESCRIPTION

  Check it is registered   launchctl list | grep extendedreach
  Run it right now         launchctl start $LABEL
  See what happened        ./.venv/bin/python -m src.main --status
  Stop the schedule        ./scripts/install_schedule.sh --uninstall

Two things this cannot do for you:

  * The Mac must be awake and you must be logged in. launchd will not wake a
    sleeping Mac for a scheduled job; a missed run fires once at next wake.
  * The portal session will eventually expire. When it does, runs stop with
    "requires_human_login" and upload nothing until you do one run by hand.
    --status says so in plain words. Check it weekly.

DONE
