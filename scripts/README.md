Scripts folder

This folder contains one-shot or job-like scripts that modify Salesforce data, perform API calls, fix sync issues, and perform support tasks such as reassigning accounts.

Conventions
- File naming: `YYYYMMDD_job-descriptive-name.(py|sh|js)` or `job-descriptive-name.(py|sh|js)` for scheduled jobs.
- Keep scripts idempotent where possible and document side effects in a per-script README.
- Credentials: store secrets in environment variables or a secrets manager; never commit keys or `.env` to the repo.
- Logging and error handling: write logs to files or stdout; exit non-zero on failure so CI/job schedulers detect errors.

Suggested layout
- `scripts/job-name.py` — The runnable job or script
- `scripts/lib/` — Optional shared helpers used by multiple scripts
- `scripts/examples/` — Optional place for example scripts or templates

Add a README within a job folder to describe when/run conditions and dependencies.