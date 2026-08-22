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

Workbooks land in `ER_EXPORT_DIR` (default `./data/exports`) named
`<slug>_YYYYMMDD.xlsx`, alongside a `manifest.json` recording what succeeded.

Useful flags:

| Flag | Effect |
|---|---|
| `--login` | Interactive sign-in; saves the session and exits |
| `--only <slug>` | Export a single report, e.g. `--only pastdue_case` |
| `--headed` | Watch it run — useful when a selector breaks |

Exit codes: `0` all reports exported · `2` one or more failed (check
`manifest.json`) · `1` unexpected error. A scheduler should alert on non-zero.

## Consuming the output

```bash
DATA_SOURCE=exports npm run dev
```

`src/lib/extendedreach/exports.ts` reads the newest workbook per slug and maps
them into the `CaseworkDataset` the app already consumes. A missing workbook
degrades that slice to empty rather than failing the whole load; a workbook that
parses to zero rows logs a warning naming the slug, which is the signal that
column headers drifted upstream.

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
