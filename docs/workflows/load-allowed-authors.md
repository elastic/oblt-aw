# Workflow: `load-allowed-authors.yml`

## Overview

Source file: [.github/workflows/load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml)

This reusable workflow reads [config/obs/allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json) and [config/obs/allowed_issue_authors.json](../../config/obs/allowed_issue_authors.json) from `elastic/oblt-aw` and exposes both allow lists as workflow outputs.

Ingress uses the **PR** outputs to gate PR-only workflows by author login and to pass `allowed-bot-users` for dependency review. Ingress uses **`allowed_issue_authors_csv`** for specialized GH-AW issue wrappers (security and resource-not-accessible triage/fixer), not for generic `gh-aw-issue-triage` / `gh-aw-issue-fixer`.

## Usage

Triggers:

- `workflow_call`

Called by ingress:

- [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml), job `load-allowed-authors`

Ingress runs this job on every supported invocation (in parallel with `dashboard-enabled-workflows`).

## API / Interface

`workflow_call` outputs:

| Output | Type | Meaning |
|--------|------|---------|
| `allowed_pr_authors_json` | JSON array string | Compact JSON array of allowed PR author logins, used by ingress `contains(fromJSON(...), github.event.pull_request.user.login)` checks |
| `allowed_pr_authors_csv` | string | Same PR logins comma-separated for workflows that accept CSV inputs (for example dependency review) |
| `allowed_issue_authors_json` | JSON array string | Compact JSON array of allowed logins for issue-scoped `allowed-bot-users` (optional use by callers) |
| `allowed_issue_authors_csv` | string | Issue allow list comma-separated for `allowed-bot-users` on issue triage/fixer paths |

## Configuration

Top-level permissions:

- `contents: read`

The job checks out **`elastic/oblt-aw`** at `main` with sparse checkout (`fetch-depth: 1`) and reads:

- `config/obs/allowed_pr_authors.json`
- `config/obs/allowed_issue_authors.json`

It then emits outputs with:

- `jq -c .` for each `*_json` output
- `jq -r 'join(",")'` for each `*_csv` output

## References

- [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md)
- [config/obs/allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json)
- [config/obs/allowed_issue_authors.json](../../config/obs/allowed_issue_authors.json)
