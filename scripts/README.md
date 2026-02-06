# Scripts

This folder contains one-shot or job-like scripts that modify Salesforce data, perform API calls, fix sync issues, and perform support tasks such as reassigning accounts.

## Available Scripts

| Folder | Description | README |
|--------|-------------|--------|
| `serp-api/` | Enriches Salesforce Accounts with Google Maps data (rating, reviews, price, type, website) via SerpApi | [README](serp-api/README.md) |

## Conventions

- **File naming**: `job-descriptive-name.(py|sh|js)` or `YYYYMMDD_job-descriptive-name.(py|sh|js)` for dated scripts.
- Keep scripts idempotent where possible and document side effects in a per-script README.
- **Credentials**: store secrets in the root `.env` file (gitignored); never commit keys.
- **Logging**: write logs to stdout; exit non-zero on failure so CI/job schedulers detect errors.
- **Output data**: write CSVs and data files to the root `data/` folder (gitignored).
