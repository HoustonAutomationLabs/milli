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

To find a selector: open the page in Chrome, right-click the element,
**Inspect**, then right-click the highlighted markup → **Copy** → **Copy
selector**.

The tool refuses to start if any working directory resolves inside this git
repository. A browser profile is an authenticated session and a downloaded
report is PHI; neither may be one `git add -A` away from being published.

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

See [`scripts/schedule_example.md`](scripts/schedule_example.md) for two
launchd examples — 6 PM daily, and every two hours during business hours —
and for why only one instance may ever run at a time.

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

## Extending to more reports

`workflow.json` keys reports by slug, so a second one is a second entry. The
POC deliberately refuses to run with more than one enabled — a config error,
not a silent choice of whichever came first.

To go multi-report later: loop over the enabled reports in `_run_workflow`,
give each its own `RunRecord`, and keep the exit code as the worst of them.
One failing report must not lose the others — the existing Node exporter in
this repository (`scripts/export-extendedreach.mjs`) already does exactly
that, and is worth reading first.

## Relationship to the rest of this repository

`scripts/export-extendedreach.mjs` is a Node exporter that already pulls
fourteen ExtendedReach reports into `data/exports` for the dashboard. It
overlaps with this tool's steps 1–9. This project adds what that one does not
have: validation before publication, duplicate suppression, a redacted
operational log, and Google Drive delivery. Before either is put into
production, decide which one owns exporting — running both means two browser
sessions on the same account and two definitions of "today's export".

See `docs/extendedreach-audit.md` for what the portal does and does not offer
(no API, no report scheduling, one-click exports only), and `CLAUDE.md` for
the data-handling rules this project inherits.
