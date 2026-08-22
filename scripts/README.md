# ExtendedReach exporter

Pulls the ten reports the dashboard needs out of ExtendedReach as Excel
workbooks, on a schedule, without a paid data feed.

ExtendedReach has no API on the agency's plan and no report-level scheduling
(see [`../docs/extendedreach-audit.md`](../docs/extendedreach-audit.md)), but
every report offers a one-click Excel export. This script drives a real browser
session to click those exports — boring automation of an authorised manual task.
It signs in as a real user, opens each report and clicks Excel. It does not
scrape rendered rows or touch anything outside the Reports area.

## Setup

```bash
npm install
npx playwright install chromium     # skip if PLAYWRIGHT_BROWSERS_PATH is set
cp .env.example .env.local          # fill in ER_BASE_URL / ER_USERNAME / ER_PASSWORD
```

## First run — interactive

Most tenants require MFA, which cannot and should not be automated. Sign in
once yourself; the authenticated session is saved for later runs.

```bash
node scripts/export-extendedreach.mjs --login
```

A browser opens, credentials are prefilled where possible, and you complete
sign-in and MFA. Press Enter in the terminal once you can see the home page.
The session is written to `.er-session.json`.

> **Treat `.er-session.json` as a credential.** It is an authenticated session
> to a system holding children's records. It is gitignored; never share or copy
> it. Re-run `--login` when it expires.

## Routine runs — unattended

```bash
node scripts/export-extendedreach.mjs
```

Exports land in `ER_EXPORT_DIR` (default `./data/exports`) named
`<slug>_YYYYMMDD.<ext>`, alongside a `manifest.json` recording what succeeded.
The extension is whatever the download actually was: most report views give
`.xlsx`, but the Compliance Tracking custom reports give `.csv` even though the
control is labelled "Excel".

Useful flags:

| Flag | Effect |
|---|---|
| `--login` | Interactive sign-in; saves the session and exits |
| `--only <slug>` | Export a single report, e.g. `--only pastdue_case` |
| `--headed` | Watch it run — useful when a selector breaks |

Exit codes: `0` all reports exported · `2` one or more failed (check
`manifest.json`) · `1` unexpected error. A scheduler should alert on non-zero.

## Reconcile the columns — do this once, before trusting the data

The column names the loader looks for came from reading ExtendedReach's screens
during the audit. Exported header text does not always match the rendered
label, and the only symptom of a mismatch is an empty dashboard.

Check a real workbook before wiring anything up:

```bash
npm run inspect:export -- ./data/exports              # whole directory
npm run inspect:export -- ./data/exports/pastdue_case_20260822.xlsx
npm run inspect:export -- ./some/file.csv --slug compliance_case
```

It reads `.xlsx` and `.csv`, and picks the report spec from the filename — so
name a file `<slug>_YYYYMMDD.<ext>` or pass `--slug`.

For each report it prints which fields resolved to which header, which did not,
what columns the file has that nothing claimed, and the exact alias line to add
to `src/lib/extendedreach/schema.ts` when something is missing. Add the alias,
re-run, repeat until it reports all reports ready. Exit code is `2` while any
report still mismatches, so CI can gate on it.

**Compliance Tracking is checked differently.** It is a matrix — one row per
case, one column per obligation — so there is no fixed field list to tick off.
Instead the tool resolves the four identity columns, counts the obligation
columns, and parses every cell, failing if any cell has a form
`parseMatrixCell` does not recognise. An unrecognised cell is the failure that
matters there: it means ExtendedReach has a status word that would otherwise be
silently miscategorised.

**The output is safe to share.** Names and free-text values are masked to their
shape (`Xxxx, Xxxxx`); only column labels, dates and categorical values
(status, type, program) print verbatim. There is an `--unmask` flag for local
debugging that prints a warning — do not use it for anything you paste
elsewhere.

## Consuming the output

```bash
DATA_SOURCE=exports npm run dev
```

`src/lib/extendedreach/exports.ts` reads the newest export per slug and maps
them into the `CaseworkDataset` the app already consumes. A missing file
degrades that slice to empty rather than failing the whole load; a file that
parses to zero rows logs a warning naming the slug, which is the signal that
column headers drifted upstream.

Not every verified report is loaded. `pastdue_case`, `pastdue_home`,
`inprocess`, `opencases` and `caseload` feed the dataset. `needapproval_case`,
`rejected_case`, `reportscompleted` and `compliance_case` are verified and
parse, but are deliberately not merged in — the compliance matrix alone carries
3,952 obligations against the task reports' 1,161, and folding it in would
change every headline number on the dashboard. That is an exec decision, not a
side effect of adding a parser.

## One thing still to confirm

The audit recorded each report's internal view code but not the URL it resolves
to. Without it the script walks the menus by link text, which works but is more
fragile. Open any report in ExtendedReach, copy the URL, and set:

```
ER_REPORT_URL_TEMPLATE=/reports/view?id={view}
```

The script then navigates directly by view code. Worth five minutes.

## If a report fails

1. Re-run with `--headed --only <slug>` and watch where it stops.
2. If it stalls at sign-in, the session expired — `--login` again.
3. If it reaches the report but finds no Excel button, the toolbar changed;
   update the selector in `exportReport()`.
4. If the menu path changed, update `menuPath` for that entry in `REPORTS`.
