# default-template

Default template to use when creating repository

## Purpose

This repository stores one-shot and job-like scripts that perform Salesforce data updates, launch API calls to resolve sync issues between Salesforce and other systems, and handle tasks like reassigning accounts. Scripts are intended to be run manually or from job schedulers and should be focused, idempotent, and well-documented.

## Folder structure

- `scripts/` — Root folder for one-shot and scheduled job scripts; use clear names and include a README for each job where needed.

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
