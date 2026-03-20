# Workflow: `ci.yml`

## Overview

Source file: `.github/workflows/ci.yml`

This workflow runs quality checks and tests on every pull request targeting `main`. It enforces pre-commit checks and Python tests, and runs TypeScript tests via `npm test`.

## Triggers

- `pull_request` on branch `main` (opened, synchronize, reopened)

## Jobs

| Job               | Purpose                                                                 |
|-------------------|-------------------------------------------------------------------------|
| `pre-commit`      | Runs all pre-commit hooks (YAML, shell, Python lint/format, mypy)            |
| `python-tests`    | Runs pytest on `tests/`                                                 |
| `typescript-tests`| Runs `npm test` (tsx) on `tests/unit/*.test.ts`                         |
| `scorecard`       | OpenSSF Scorecard security analysis; uploads SARIF to GitHub Security   |
| `required`        | Gate job; fails if any of the above jobs fail                           |

## Pre-commit Hooks

The `pre-commit` job uses `elastic/oblt-actions/pre-commit@v1`, which runs all hooks defined in `.pre-commit-config.yaml`:

- **YAML**: yamllint with `.yamllint.yml`
- **Shell**: ShellCheck on shell scripts
- **Python**: ruff (lint + format), mypy (strict) on `scripts/`
- **License**: Apache 2.0 headers and NOTICE sync (`scripts/update_license_files.py`; excludes `*.yml` / `*.yaml`)
- **General**: trailing whitespace, EOF, YAML/JSON checks, merge conflict detection, line endings
- **Action pinning**: Enforced by workflow design (trusted actions use tags; untrusted use SHA). Ratchet is not used because sethvargo/ratchet lacks `.pre-commit-hooks.yaml` and our policy uses tags for trusted namespaces.

On PRs, pre-commit runs only on changed files (`--from-ref` / `--to-ref`).

## Python Tests

- Python 3.13
- Dependencies: pytest 8.3.5
- Command: `pytest tests/ -v --tb=short`
- Pip cache keyed by `**/*.py`, `pyproject.toml`, `requirements*.txt`

## TypeScript Tests

- Node.js 20
- Dependencies: `npm ci` (from `package-lock.json`)
- Command: `npm test` → `tsx --test tests/unit/*.test.ts`
- npm cache enabled via `actions/setup-node`
- Note: CI currently runs TypeScript tests only; dedicated TypeScript lint/format/type-check jobs are not part of this workflow.

## Scorecard

- Runs OpenSSF Scorecard with SARIF output
- Uploads results to GitHub Code Scanning (Security tab)
- Uses OIDC (`id-token: write`); no long-lived credentials

## Permissions

- All jobs: `contents: read` (minimal)
- Scorecard: `security-events: write`, `id-token: write`

## References

- Pre-commit config: `.pre-commit-config.yaml`
- Local development: `docs/development/contributing.md`
