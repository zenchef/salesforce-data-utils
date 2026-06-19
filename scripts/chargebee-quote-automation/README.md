# Chargebee Quote Automation (Selenium)

This tool automates two Chargebee quote actions in Salesforce **Classic** for the
platform migration project: **Generate Quote PDF** and **Sync to Opportunity**.
It reads a CSV of quote identifiers, resolves each record via the Salesforce API,
then drives Firefox to click the buttons that have no API equivalent.

Originally a standalone repository (`salesforce-click-automation`), it has been
refactored into this repo's modular layout and now uses `simple-salesforce`
(shared with the rest of the repo) instead of the internal `pyzenchef` package.

## Logic Overview

1. **Read**: Loads quote identifiers from the CSV column (`--id-column`, default `Name`).
2. **Resolve**: For each identifier, queries `chargebeeapps__CB_Quote__c` to get the
   record `Id` and the fields used by the optimized re-run check.
   - Identifiers starting with `ZCQUO-` are matched on `Name`; otherwise on `Id`.
3. **Automate**: Navigates Firefox (already logged in via SSO) to each record and clicks:
   - **Generate Quote PDF** → confirm.
   - **Sync to Opportunity** → confirm.
4. **Resume**: On failure, re-run with `--start-from <index>` to continue from the last
   successful record, or use `--optimized` to skip actions already completed.

## Directory Structure

```text
salesforce-data-utils/
├── .env                        # Credentials (gitignored, at repo root)
├── requirements.txt            # Python dependencies
└── scripts/
    └── chargebee-quote-automation/
        ├── main.py                 # Entry point & orchestration
        ├── config.py               # Config & Salesforce auth
        ├── salesforce_client.py    # Salesforce quote lookups (read-only)
        └── browser_automation.py   # Selenium/Firefox UI actions
```

## Prerequisites

1. **Install dependencies** (from repo root):
   ```bash
   pip install -r requirements.txt
   ```
2. **Install Firefox** — [download here](https://www.mozilla.org/en-US/firefox/new/).
3. **Log in to Salesforce** in Firefox via SSO.
4. **Switch Salesforce to Classic** — the targeted buttons do **not** exist in
   Lightning Experience; the script will not work there.
5. **Find your Firefox profile path** — open `about:profiles`, copy the active
   profile's "Root Directory".

## Configuration

Set the following in the repo-root `.env` (see `.env.example`):

```env
# Salesforce (shared across the repo)
SF_USERNAME=your_username
SF_PASSWORD=your_password
SF_TOKEN=your_security_token

# Firefox profile already logged in to Salesforce via SSO
FIREFOX_PROFILE_PATH=/path/to/Firefox/Profiles/xxxx.default-release
```

The Salesforce instance URL is derived automatically from the API session, so no
hostname needs to be configured.

## Usage

All commands are run from the repo root.

### Full run
```bash
python scripts/chargebee-quote-automation/main.py --csv data/quotes.csv
```

### Custom identifier column
```bash
python scripts/chargebee-quote-automation/main.py --csv data/quotes.csv --id-column QuoteId
```

### Resume after a failure
Re-run starting from the last successfully processed row index:
```bash
python scripts/chargebee-quote-automation/main.py --csv data/quotes.csv --start-from 300
```

### Optimized re-run
Skip actions that already completed (PDF link present, opportunity already synced):
```bash
python scripts/chargebee-quote-automation/main.py --csv data/quotes.csv --optimized
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--csv` | *(required)* | Path to the CSV of quote identifiers |
| `--id-column` | `Name` | CSV column holding the quote Name or record Id |
| `--start-from` | `0` | Row index to resume from after a failure |
| `--optimized` | off | Skip actions already completed for a record |

## Troubleshooting

**Issue**: Buttons are never found / timeouts.
**Solution**: Confirm Salesforce is in **Classic** mode and the Firefox profile is
logged in via SSO.

**Issue**: The run stops partway through.
**Solution**: Note the last `RECORD <index>` logged, then re-run with
`--start-from <index>`. For large batches, `--optimized` avoids redoing finished work.
