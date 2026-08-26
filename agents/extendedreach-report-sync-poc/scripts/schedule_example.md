# Scheduling on macOS

Two launchd examples, and one rule that matters more than either.

`launchd` is macOS's own scheduler. It is preferred over `cron` here because
it survives reboots, logs its own failures, and does not need a terminal
window open. The `--schedule` flag in `src/main.py` uses APScheduler instead
and is fine for testing, but it only runs while you leave the process running.

Before you schedule anything, get one headed run working by hand. A scheduled
job that has never succeeded interactively will simply fail on a timer.

---

## Only one instance may run at a time

**This is not optional.** Two concurrent runs share one Chromium profile
directory, and Chromium does not tolerate that: the second process can corrupt
the profile, which destroys the saved session and forces a fresh interactive
sign-in.

Three things enforce it, and you should keep all three:

1. `src/main.py` takes an exclusive `flock` on `er_sync.lock` in the log
   directory. A second run exits immediately with code `7` and logs
   `another_run_in_progress`. It does not wait, and it does not fail loudly —
   an overlap is not an error worth waking anyone for.
2. `launchd` gets `ThrottleInterval` so it will not restart a job in a tight
   loop.
3. Each schedule below uses **one** `.plist` with **one** label. Do not load
   both examples at once — they would overlap by design.

Exit code `7` in your logs means the lock did its job. Exit code `3`
(`requires_human_login`) means the session expired and a person must run
`./scripts/run_once.sh` headed once to sign in again. Schedule nothing that
tries to handle code `3` automatically; there is nothing to automate.

---

## 1. Every day at 6:00 PM

Save as `~/Library/LaunchAgents/com.agency.extendedreach-report-sync.plist`.

TODO(operator): replace `/Users/YOU/path/to/extendedreach-report-sync-poc`
with the real path, and confirm 18:00 is the time you want.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agency.extendedreach-report-sync</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOU/path/to/extendedreach-report-sync-poc/scripts/run_once.sh</string>
        <string>--headless</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/YOU/path/to/extendedreach-report-sync-poc</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

    <!-- Never restart on its own. A failure here means a person should look. -->
    <key>KeepAlive</key>
    <false/>
    <key>RunAtLoad</key>
    <false/>
    <key>ThrottleInterval</key>
    <integer>300</integer>

    <!-- launchd's own capture of stdout/stderr. The application's redacted
         log is the one to read; keep these OUTSIDE the repository too. -->
    <key>StandardOutPath</key>
    <string>/Users/YOU/er-sync/logs/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOU/er-sync/logs/launchd.err.log</string>
</dict>
</plist>
```

Load, verify, unload:

```bash
launchctl load  ~/Library/LaunchAgents/com.agency.extendedreach-report-sync.plist
launchctl list | grep extendedreach          # second column is the last exit code
launchctl start com.agency.extendedreach-report-sync    # fire once, now
launchctl unload ~/Library/LaunchAgents/com.agency.extendedreach-report-sync.plist
```

---

## 2. Every two hours during business hours

`StartCalendarInterval` accepts an array of times. Listing each hour is more
verbose than an interval but far more predictable: it fires at exact times
rather than drifting from whenever the job was last loaded.

8 AM, 10 AM, 12 PM, 2 PM, 4 PM, 6 PM. TODO(operator): confirm these hours,
and note the duplicate check means the extra runs cost almost nothing — the
second run of the day finds the first upload's run key and skips.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agency.extendedreach-report-sync-business-hours</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOU/path/to/extendedreach-report-sync-poc/scripts/run_once.sh</string>
        <string>--headless</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/YOU/path/to/extendedreach-report-sync-poc</string>

    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>14</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
    </array>

    <key>KeepAlive</key>
    <false/>
    <key>RunAtLoad</key>
    <false/>
    <!-- Longer than a normal run, so an overrun cannot be relaunched on top
         of itself. Raise it if your report takes more than 20 minutes. -->
    <key>ThrottleInterval</key>
    <integer>1200</integer>

    <key>StandardOutPath</key>
    <string>/Users/YOU/er-sync/logs/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOU/er-sync/logs/launchd.err.log</string>
</dict>
</plist>
```

launchd has no weekday-only field inside `StartCalendarInterval` arrays that
combines cleanly with hours. If you need weekdays only, add a `Weekday` key to
each dict (`1`–`5`, Monday–Friday):

```xml
<dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>8</integer>
    <key>Minute</key><integer>0</integer>
</dict>
```

…repeated for each weekday and hour. It is long. It is also unambiguous, which
at 8 AM on a Monday is worth more than brevity.

---

## Things that will bite you

- **The Mac must be awake.** launchd will not wake a sleeping Mac for a
  `StartCalendarInterval` job. A missed run fires once at the next wake. If
  the schedule must be reliable, use a machine that stays on.
- **Full Disk Access.** macOS may prompt the first time a launchd job writes
  to certain directories. Keep the working directories in your home folder to
  avoid it.
- **`--headless` needs a live session.** The Chromium profile keeps you signed
  in, but sessions expire. When one does, the run exits `3` and a person must
  do one headed run. Watch for code `3` rather than being surprised by a
  silently empty Drive folder.
- **Check `runs.jsonl`, not the Drive folder.** A folder with no new file
  today means either "nothing to upload" or "six failed runs". Only the run
  log distinguishes them.
