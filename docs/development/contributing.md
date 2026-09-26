# Contributing to oblt-aw

## Overview

This guide covers local setup and quality checks for contributors. All changes must pass CI before merge.

For goal-oriented **maintainer stories** (add a workflow, change maturity, ephemeral tokens), see [docs/guides/maintainer/](../guides/maintainer/).

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
pre-commit install --hook-type pre-commit --hook-type pre-push
```

This installs the hooks from [.pre-commit-config.yaml](../../.pre-commit-config.yaml). They run on `git commit` and `git push`. Agents must also follow the GOLD rule [.cursor/rules/ci-precommit-before-push.mdc](../../.cursor/rules/ci-precommit-before-push.mdc).

### 3. Install Python dependencies

```bash
pip install -r requirements-ci.txt  # includes requirements-runtime.txt (PyYAML) and pytest
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

### gh-aw workflow compile check (required when editing workflow sources)

If you touch a gh-aw workflow source or shared fragment, regenerate and validate the compiled workflow lock files before pushing:

```bash
make compile-aw-check
```

This command installs the pinned gh-aw compiler, recompiles the generated `.lock.yml` files under `.github/workflows/`, and fails if the checked-in outputs drift from the source markdown. Do not hand-edit the lock files; edit the source `.md` and rerun this command.

### Python tests

```bash
pytest tests/unit tests/integration -v --tb=short
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

## GitHub Actions checkout hardening

When adding or editing workflow steps that use `actions/checkout@v7`, set `persist-credentials: false` explicitly:

```yaml
- uses: actions/checkout@v7
  with:
    persist-credentials: false
```

Keep existing checkout options (`repository`, `token`, `path`, `fetch-depth`, `sparse-checkout`, etc.) and add `persist-credentials: false` alongside them.

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

The CI workflow ([.github/workflows/ci.yml](../../.github/workflows/ci.yml)) runs on every pull request (any base branch). See [docs/workflows/ci.md](../workflows/ci.md) for details.

## References

- CI workflow: [docs/workflows/ci.md](../workflows/ci.md)
- Pre-commit config: [.pre-commit-config.yaml](../../.pre-commit-config.yaml)
- Workflow catalog: [docs/workflows/README.md](../workflows/README.md)
