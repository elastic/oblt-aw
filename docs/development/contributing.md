# Contributing to oblt-aw

## Overview

This guide covers local setup and quality checks for contributors. All changes must pass CI before merge.

## Prerequisites

- Python 3.14
- Node.js 24
- [pre-commit](https://pre-commit.com/)

## One-time Setup

### 1. Install pre-commit

```bash
pip install pre-commit
# or: brew install pre-commit
```

### 2. Install pre-commit hooks

```bash
pre-commit install
```

This installs the hooks from [.pre-commit-config.yaml](../../.pre-commit-config.yaml). They run automatically on `git commit`.

### 3. Install Python dependencies

```bash
pip install pytest==9.0.2
```

### 4. Install Node.js dependencies

```bash
npm ci
```

## Running Checks Locally

### All pre-commit hooks (recommended before pushing)

```bash
pre-commit run --all-files
```

> **macOS Python.org installer:** If you see `SSL: CERTIFICATE_VERIFY_FAILED` when pre-commit installs hooks, this is the classic Python.org macOS certificate issue. Run the bundled installer: `/Applications/Python 3.xx/Install Certificates.command`

### Python tests

```bash
pytest tests/ -v --tb=short
```

### TypeScript tests

```bash
npm test
```

### License automation

Update license headers and NOTICE files:

```bash
make update-license
# or: python3 scripts/update_license_files.py
```

Verify without modifying (useful for CI):

```bash
make update-license-check
# or: python3 scripts/update_license_files.py --check
```

License headers are not applied to `*.yml` or `*.yaml` files (including GitHub Actions workflows).

The `update-license-files` hook uses `always_run: true` in [.pre-commit-config.yaml](../../.pre-commit-config.yaml) so the script runs on every pre-commit invocation and rescans all header targets (not only when certain file types are staged).

### Individual tools

Use pre-commit hook entrypoints for one-off tool runs so you use the pinned hook versions without extra global installs:

- **YAML lint**: `pre-commit run yamllint --all-files`
- **Shell lint**: `pre-commit run shellcheck --all-files`
- **GitHub Actions lint**: `pre-commit run actionlint --all-files`
- **Python lint**: `pre-commit run ruff --all-files`
- **Python format**: `pre-commit run ruff-format --all-files`
- **Python type-check**: `pre-commit run mypy --all-files`

## Pre-commit Hooks

The following hooks run on commit (and in CI via the pre-commit job):

| Hook            | Scope                    | Purpose                          |
|-----------------|--------------------------|----------------------------------|
| yamllint        | `*.yml`, `*.yaml`        | YAML style and structure         |
| shellcheck      | Shell scripts            | Shell script linting             |
| actionlint      | GitHub Actions workflows | GitHub Actions workflow linting  |
| ruff            | Python files (repo-wide) | Python lint (with `--fix`)       |
| ruff-format     | Python files (repo-wide) | Python formatting                |
| mypy            | `scripts/**/*.py`        | Python type-checking (strict)    |
| update-license-files | Scripts, shell, TypeScript tests, NOTICE | Apache 2.0 headers, NOTICE sync |
| pre-commit-hooks| Various                  | Trailing whitespace, EOF, etc.   |

## CI Workflow

The CI workflow ([.github/workflows/ci.yml](../../.github/workflows/ci.yml)) runs on every PR to `main`. See [docs/workflows/ci.md](../workflows/ci.md) for details.

## References

- CI workflow: [docs/workflows/ci.md](../workflows/ci.md)
- Pre-commit config: [.pre-commit-config.yaml](../../.pre-commit-config.yaml)
- Workflow catalog: [docs/workflows/README.md](../workflows/README.md)
