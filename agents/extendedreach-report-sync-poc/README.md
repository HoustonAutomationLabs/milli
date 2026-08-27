# extendedreach-report-sync-poc

A local proof of concept: at a scheduled time, open one ExtendedReach report
in an already-authorised browser profile, export it, validate the file, and
upload it to one Google Drive folder.

**It is read-only.** It never creates, edits, deletes, submits, approves or
rejects anything in the portal. That is enforced in three places, not just
promised in a README:

| Guard | Where | What it stops |
|---|---|---|
| Action allow-list | `config.READ_ONLY_ACTIONS` | A workflow step whose action could write is refused at config time |
| URL denylist | `workflow.json → safety.url_denylist_substrings` | Navigation to any URL containing `delete`, `submit`, `approve`, … |
| Filter value pattern | `config.FILTER_VALUE_PATTERN` | Free text — and therefore names — being typed into a portal field |

**It will not work against the live portal yet.** The report URL, the
selectors, the expected CSV headers, the Drive folder and an authorised
account all have to be supplied first. Every one of them is marked `TODO` in
`.env.example` and `config/workflow.example.json`. Until they are filled in,
`--validate-config` will tell you exactly what is missing, and no claim is
made here that the automation works end to end.

What *has* been verified: the offline test suite (85 tests) covering filename
generation, file validation, configuration validation and log redaction.

---

## Requirements

- macOS
- Python 3.11 or newer (`python3 --version`)
- An ExtendedReach account you are explicitly authorised to use, and a report
  you are explicitly authorised to export
- A Google Cloud project with the Drive API enabled

---

## Setup

```bash
cd agents/extendedreach-report-sync-poc
./scripts/install_playwright.sh
```

That creates `.venv`, installs the dependencies, downloads Chromium and runs
the test suite.

### Configure

```bash
cp .env.example .env
cp config/workflow.example.json config/workflow.json
```

Edit both and replace every `TODO`. The values you need:

| Where | Value | How to find it |
|---|---|---|
| `.env` | `EXTENDEDREACH_BASE_URL` | The portal address you sign in to |
| `.env` | `REPORT_SLUG` | A short name of your choosing, e.g. `pastdue_case` |
| `.env` | `EXTENDEDREACH_REPORT_URL` *(optional)* | Open the report, copy the address bar |
| `.env` | `EXPECTED_CSV_HEADERS` | Download the report by hand once, open it, copy the column names |
| `.env` | `GOOGLE_DRIVE_FOLDER_ID` | The part of the folder's URL after `/folders/` |
| `.env` | the four `*_DIR` paths | Anywhere **outside** this repository |
| `workflow.json` | `auth.authenticated_selector` | An element that appears only when signed in — a sign-out link, an account menu |
| `workflow.json` | `auth.mfa_selectors` | The MFA code field, so the tool can recognise a challenge and stop |
| `workflow.json` | `reports.<slug>.export` | The export control on the report page |

#### Let the setup assistant find the selectors

Rather than doing that by hand:

```bash
./.venv/bin/python -m src.main --setup-assist
```

It opens a browser and walks you through three steps: sign in, open the
report you want, point at the export button. It **clicks nothing, downloads
nothing and changes nothing** — it reads the page's structure and prints
numbered candidates for you to choose from. It writes
`config/workflow.draft.json`; review it, then:

```bash
cp config/workflow.draft.json config/workflow.json
```

If you would rather do it by hand: open the page in Chrome, right-click the
element, **Inspect**, then right-click the highlighted markup → **Copy** →
**Copy selector**.

The MFA selector is the one the assistant usually cannot capture, because no
challenge is on screen while you are signed in. Leave it as-is if you like —
the run still stops safely on a challenge, just less specifically.

The tool refuses to start if any working directory resolves inside this git
repository. A browser profile is an authenticated session and a downloaded
report is PHI; neither may be one `git add -A` away from being published.

### Lost? Ask what to do next

```bash
./.venv/bin/python -m src.main --doctor
```

It prints a nine-point setup checklist showing what is done, what is not, and
**one** command to run next. Run it any time you are unsure where you are.

### Check the configuration

```bash
./.venv/bin/python -m src.main --validate-config
```

This opens no browser and touches no network. It lists every problem at once.
Exit code `2` means something is still missing.

### Check the validation logic, offline

```bash
./.venv/bin/python -m src.main --test-download-fixture
```

Generates synthetic sample files and validates them, with no access to
ExtendedReach at all. Two samples are *supposed* to fail: a truncated export
and an HTML error page saved with an `.xlsx` name. If those two pass, the
validation is broken.

The samples are generated rather than committed, for two reasons: a real
sample would be case data, and this repository's `.gitignore` excludes `*.csv`
and `*.xlsx` outright, so a committed fixture would silently not exist for
anyone who cloned.

---

## Authorise Google Drive

`docs/Claude-in-Chrome-Prompts.pdf` has copy-paste prompts for this section
and for creating the Drive folders, if you would rather not click through the
Console by hand. It covers only those two tasks: they involve no case data.
**Never point a browser assistant at ExtendedReach itself** — an assistant that
reads a page to decide what to click would be reading children's records, and
the portal has approve, reject and delete controls on the same screens as
export. The read-only guarantees in this tool are structural; an assistant has
no equivalent.

1. In the [Google Cloud Console](https://console.cloud.google.com/), create or
   pick a project.
2. **APIs & Services → Library →** enable **Google Drive API**.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID →
   Desktop app.**
4. Download the JSON. Save it **outside this repository**, at the path in
   `GOOGLE_CREDENTIALS_FILE`.
5. The first non-dry run opens a browser for consent and writes a token to
   `GOOGLE_TOKEN_FILE`. Later runs reuse it without prompting.

### About the scope

The default is `drive.file` — this app can see and manage only the files it
created. That is enough for the duplicate check, because the files it looks
for are its own previous uploads.

If uploads fail with a 403 on the folder, the folder was not created by this
app and Google will not let a `drive.file` client write into it. Prefer
letting the tool create its own subfolder over widening to the full `drive`
scope, which grants read/write across the entire Drive.

### Before you point this at a real export

Consumer Google accounts — anything `@gmail.com` — are **not covered by a
Google BAA**. Drive is HIPAA-eligible only in a paid Workspace tenant whose
admin has accepted the BAA and where Drive is in the covered-services list.
These reports carry names, dates of birth, SSNs and Medicaid numbers.
Confirm the destination folder lives in a covered tenant, or keep this
pointed at de-identified files.

---

## First run

Headed, and without uploading anything:

```bash
./scripts/run_once.sh --dry-run
```

A Chromium window opens on the persistent profile. The first time, you will
not be signed in — the tool prints a prompt and **waits for you** to sign in
and complete MFA yourself. It will not type a username, a password, an MFA
code, or touch a CAPTCHA. Once it can see the configured signed-in element, it
continues on its own.

The session is saved in the browser profile, so later runs start already
signed in until it expires.

`--dry-run` navigates, exports, saves and validates — then stops. Nothing
reaches Google Drive. Check the downloaded file yourself before you run
without it.

When you are satisfied:

```bash
./scripts/run_once.sh
```

### Commands

```bash
python -m src.main --validate-config          # config only, no browser
python -m src.main --test-download-fixture    # validation only, no portal
python -m src.main --once --dry-run           # everything except the upload
python -m src.main --once                     # the full workflow
python -m src.main --once --headless          # no window; needs a live session
python -m src.main --doctor                   # where am I? what's next?
python -m src.main --list-reports             # every configured report
python -m src.main --setup-assist             # capture URL + selectors
python -m src.main --status                   # recent runs; is it working?
python -m src.main --schedule                 # local APScheduler loop
python -m pytest                              # the test suite
```

`--headed` is the default. `--headless` fails with `requires_human_login`
rather than trying to sign in on its own.

### Exit codes

| Code | Meaning | What to do |
|---|---|---|
| 0 | Success, or a duplicate correctly skipped | Nothing |
| 1 | Unexpected error | Read `runs.jsonl` |
| 2 | Configuration invalid | `--validate-config` |
| 3 | A person must sign in | One headed run |
| 4 | The file failed validation | See the error category; the export may be an error page |
| 5 | Navigation or download failed | Usually a portal change — check the selectors |
| 6 | Drive upload failed | Check the folder id and the scope |
| 7 | Another run is already in progress | Nothing; the lock worked |

---

## Scheduling

```bash
./scripts/install_schedule.sh daily             # 6:00 PM every day
./scripts/install_schedule.sh business-hours    # 8,10,12,2,4,6 Mon-Fri
./scripts/install_schedule.sh --uninstall       # stop it
```

This writes the launchd `.plist` with your real paths, validates it and loads
it. No XML editing.

It refuses to install a schedule until the configuration validates **and** the
job has succeeded at least once by hand. A timer on something that has never
worked only automates the failure. `--force` overrides that if you have a
reason.

[`scripts/schedule_example.md`](scripts/schedule_example.md) has the same
plists written out, for when you want to change the hours yourself, plus why
only one instance may ever run at a time.

### Two things a schedule cannot do for you

**The Mac must be awake and you must be logged in.** launchd will not wake a
sleeping Mac for a scheduled job. A missed run fires once at the next wake. If
this has to be reliable, it needs a machine that stays on.

**The portal session will expire.** The browser profile keeps you signed in
for a while, but not forever. When it lapses, runs stop with
`requires_human_login` and upload nothing — correctly, since the alternative
would be automating sign-in. You then do one headed run and it resumes.

That second one is the reason to check in weekly:

```bash
./.venv/bin/python -m src.main --status
```

It prints the recent runs and says in plain words whether anything needs you.
An empty Drive folder on its own cannot tell you whether there was nothing to
upload or six failed runs; this can.

---

## What it writes, and where

Everything lives outside the repository, at paths you set in `.env`:

| Path | Contents | Sensitivity |
|---|---|---|
| `BROWSER_PROFILE_DIR` | Chromium profile | **An authenticated session. Treat as a credential.** |
| `DOWNLOAD_DIR` | Exported reports | **PHI once pointed at a real report** |
| `LOG_DIR/runs.jsonl` | One JSON object per run | Redacted; records that PHI moved, never its content |
| `LOG_DIR/er_sync.log` | Application log | Redacted |
| `SCREENSHOT_DIR` | Failure screenshots | Opt-in; see below |
| `GOOGLE_TOKEN_FILE` | Drive OAuth token | **A credential** |

A run record looks like this:

```json
{"run_id": "20260826-180503-a1b2c3", "report_slug": "pastdue_case",
 "started_at": "2026-08-26T18:05:03+00:00", "ended_at": "2026-08-26T18:05:41+00:00",
 "status": "success", "error_category": null,
 "local_filename": "extendedreach_pastdue_case_2026-08-26_180503.csv",
 "drive_file_id": "1AbC...", "run_key": "extendedreach:pastdue_case:2026-08-26",
 "dry_run": false, "notes": []}
```

`status` is one of `success`, `skipped`, `failed`, `requires_human_login`.
`error_category` comes from a fixed vocabulary and is never an exception
message — browser exceptions routinely quote page content, and page content
here is case data.

### Screenshots

Off by default (`SCREENSHOT_ON_FAILURE=false`). When enabled, a screenshot is
captured **only** if the page is on a surface `workflow.json` marks
screenshot-safe (a login or error page), or if the session is not
authenticated and the page therefore cannot be showing case data.

On a report page, the tool deliberately captures **nothing** and records the
redacted URL path instead. A screenshot of a report is a screenshot of
children's records. Screenshots are never uploaded to Drive.

---

## Duplicate suppression

Every upload carries `appProperties.runKey` — the report slug plus the
calendar date. Before uploading, the tool queries the folder for that key and
skips if it finds one, falling back to a filename-prefix match so a file
placed by hand still counts.

So the every-two-hours schedule uploads once a day and skips the rest, and a
manual re-run after a failure will not produce a second copy.

If a report legitimately needs uploading more than once a day, change the
granularity in `validators.build_run_key` — and change
`filename_prefix_for_run_key` to match. `tests/test_filenames.py` enforces
that the two stay consistent, because a mismatch would silently re-upload
every single day.

---

## When something goes wrong

The design goal is that failures are loud and safe, never silent and clever.

| Situation | What happens |
|---|---|
| Session expired | Headed: waits for you. Headless: exits `3`, uploads nothing |
| MFA or CAPTCHA appears | Never automated. Stops, exits `3` |
| Portal layout changed | `portal_structure_changed`, exits `5`. It does not guess at a different element |
| Export is an error page | Caught by validation, exits `4`. **Nothing is uploaded** |
| Columns renamed | `csv_headers_missing` naming the *expected* columns, exits `4` |
| Two runs overlap | The second exits `7` immediately |
| Drive rejects the upload | Exits `6`. The local file is kept |

Upload happens only after validation passes. There is no path through the code
where an unvalidated file reaches Drive.

---

## Multiple reports

Every **enabled** report in `workflow.json` runs on each scheduled run, in one
browser session. One sign-in covers all of them, which matters at nine reports:
opening the browser nine times would mean nine chances for the session check to
be the thing that fails.

```bash
python -m src.main --list-reports              # what is configured
python -m src.main --once                      # every enabled report
python -m src.main --once --report openbeds    # just one
python -m src.main --status                    # latest run of each
python -m src.main --status --report openbeds  # one report's history
```

Add a report by running `--setup-assist` again. It is **additive** — it adds
one report per run and keeps the ones already captured. Run it nine times for
nine reports.

```bash
python -m src.main --setup-assist --report openbeds
```

Three things are per-report, because with nine reports a single global setting
is wrong for eight of them:

| Setting | Where | Falls back to |
|---|---|---|
| Expected columns | `validation.expected_csv_headers` | `EXPECTED_CSV_HEADERS` |
| Minimum file size | `validation.min_file_bytes` | `MIN_FILE_BYTES` |
| Drive folder | `drive_folder_id_env` | `GOOGLE_DRIVE_FOLDER_ID` |

An explicit empty column list means "do not check this report's columns" and is
honoured; removing the key falls back instead.

**One failure never loses the others.** A broken selector on one report is
recorded against that report and the run continues; the exit code reports the
worst outcome so a scheduler still alerts. `--status` says which report failed
and, when the others are fine, that it is that report's own problem rather than
the session — the distinction that decides whether you fix a selector or just
sign in again.

`REPORT_SLUG` in `.env` no longer decides what a run covers. It only names a
default for single-report commands. A stale slug quietly exporting one report
out of nine would be the worst kind of failure: silent and plausible.

Retire a report with `"enabled": false` rather than deleting it, so what you
captured about it survives.

### Relationship to the Node exporter

`scripts/export-extendedreach.mjs` in this repository pulls fourteen reports
into `data/exports` for the dashboard and overlaps with this tool. Now that
both are multi-report, decide which one owns exporting — running both means two
browser sessions on the same account and two definitions of "today's export".

See `docs/extendedreach-audit.md` for what the portal does and does not offer
(no API, no report scheduling, one-click exports only), and `CLAUDE.md` for
the data-handling rules this project inherits.
