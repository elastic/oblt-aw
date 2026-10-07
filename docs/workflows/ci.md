# Workflow: `ci.yml`

## Overview

Source file: [.github/workflows/ci.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/ci.yml)

This workflow runs quality checks and tests on every pull request (any base branch). It enforces pre-commit checks (including Actionlint), Python unit and integration tests (`tests/unit`, `tests/integration`; not live `tests/e2e/`), TypeScript tests via `npm test`, and gh-aw lock drift (`make compile-aw-check`). Live E2E is **not** a PR gate — it runs on promote (`aw-release-promote` → `e2e-all`) and via manual `e2e-all` / leaf dispatch.

## Triggers

- `pull_request` on any base branch (opened, synchronize, reopened)

## Jobs

| Job | Purpose |
|-----|---------|
| `ci-gate` | Skips work jobs for same-repo E2E fixture PRs (`e2e:*` on `e2e/*`) |
| `gh-aw-drift` | Runs `make compile-aw-check` (recompile locks; fail on drift) |
| `pre-commit` | Runs all pre-commit hooks (YAML, shell, GitHub Actions lint, Python lint/format, mypy) |
| `python-tests` | Runs pytest on `tests/unit` and `tests/integration` (not `tests/e2e`) and validates every `*-aw-*` workflow calls `aw-prelude.yml` |
| `required` | Gate job; fails if any required job failed |
| `scorecard` | OpenSSF Scorecard security analysis; uploads SARIF to GitHub Security |
| `typescript-tests` | Runs `npm test` (tsx) on `tests/unit/*.test.ts` |

## Pre-commit Hooks

The `pre-commit` job uses [elastic/oblt-actions/pre-commit@v1](https://github.com/elastic/oblt-actions/blob/v1/pre-commit), which runs all hooks defined in [.pre-commit-config.yaml](https://github.com/elastic/oblt-aw/blob/main/.pre-commit-config.yaml):

- **YAML**: yamllint with `.yamllint.yml`
- **Shell**: ShellCheck on shell scripts
- **GitHub Actions**: actionlint on workflow definitions
- **Python**: ruff + ruff-format on Python files repo-wide; mypy (strict) on `scripts/`
- **License**: Apache 2.0 headers and NOTICE sync ([scripts/update_license_files.py](https://github.com/elastic/oblt-aw/blob/main/scripts/update_license_files.py); excludes `*.yml` / `*.yaml`)
- **General**: trailing whitespace, EOF, YAML/JSON checks, merge conflict detection, line endings
- **Action pinning**: Enforced by workflow design (trusted actions use tags; untrusted use SHA). Ratchet is not used because sethvargo/ratchet lacks `.pre-commit-hooks.yaml` and our policy uses tags for trusted namespaces.

On PRs, pre-commit runs only on changed files (`--from-ref` / `--to-ref`).

## Python Tests

- Python 3.14
- Dependencies: `requirements-ci.txt` (includes `requirements-runtime.txt` and pytest)
- Command: `pytest tests/unit tests/integration -v --tb=short` (excludes live `tests/e2e/`)
- Integration slice (no live model): `tests/integration/test_estc_pr_buildkite_detective.py` with fixtures in `testdata/agentic/estc-pr-buildkite-detective/` — see [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)
- Pip cache via `actions/setup-python` (`cache: pip`), keyed by `requirements-ci.txt` and `requirements-runtime.txt`

## TypeScript Tests

- Node.js 24
- Dependencies: `npm ci` (from `package-lock.json`)
- Command: `npm test` → `tsx --test tests/unit/*.test.ts`
- npm cache enabled via `actions/setup-node`
- Note: CI currently runs TypeScript tests only; dedicated TypeScript lint/format/type-check jobs are not part of this workflow.

## gh-aw drift

- `gh-aw-drift` always runs on non-fixture PRs (`make compile-aw-check`).
- Live lock provenance is gated at promote time via [`e2e-all.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-all.yml) from [`aw-release-promote.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/aw-release-promote.yml) — see [agentic-release-model](../operations/agentic-release-model.md).

## Scorecard

- Runs OpenSSF Scorecard with SARIF output
- Uploads results to GitHub Code Scanning (Security tab)
- Uses OIDC (`id-token: write`); no long-lived credentials

## Permissions

- Most jobs: `contents: read` (minimal)
- Scorecard: `security-events: write`, `id-token: write`

## References

- Pre-commit config: [.pre-commit-config.yaml](https://github.com/elastic/oblt-aw/blob/main/.pre-commit-config.yaml)
- Local development: [docs/development/contributing.md](../development/contributing.md)
- Testing platform design (unit through E2E, release gates): [docs/architecture/agentic-workflow-testing-platform.md](../architecture/agentic-workflow-testing-platform.md)
- Agentic release model (promote/rollback): [docs/operations/agentic-release-model.md](../operations/agentic-release-model.md)
- E2E orchestrator: [.github/workflows/e2e-all.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-all.yml)
