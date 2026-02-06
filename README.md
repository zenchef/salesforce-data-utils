# salesforce-data-utils

Utilities and scripts for Salesforce data operations — enrichment, syncing, cleanup, and bulk updates.

## Folder Structure

```text
salesforce-data-utils/
├── .env                  # Credentials (gitignored)
├── .env.example          # Credentials template
├── requirements.txt      # Python dependencies
├── data/                 # Output data (CSVs, gitignored)
└── scripts/              # All scripts and tools
    └── serp-api/         # Google Maps enrichment for SF Accounts
```

## Development Setup

### Install mise

[mise](https://mise.jdx.dev) manages tool versions for this project.

```bash
curl https://mise.run | sh
```

Activate mise in your shell (add to ~/.zshrc or ~/.bashrc):

```bash
eval "$(mise activate zsh)"  # or bash
```

### Install project tools

```bash
mise install
```

This installs tools defined in `mise.toml` (currently: pre-commit).

### Set up pre-commit hooks

```bash
pre-commit install
```

This enables [pre-commit](https://pre-commit.com) hooks that run automatically on each commit.

### Installing additional tools (examples)

```bash
mise install go@1.25
mise install awscli
```
