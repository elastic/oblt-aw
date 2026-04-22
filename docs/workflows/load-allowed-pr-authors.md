# Workflow: `load-allowed-pr-authors.yml`

## Overview

Source file: [.github/workflows/load-allowed-pr-authors.yml](../../.github/workflows/load-allowed-pr-authors.yml)

This reusable workflow reads [config/obs/allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json) from `elastic/oblt-aw` and exposes the allow list as workflow outputs.

Ingress uses those outputs to gate PR-only workflows by author login.

## Usage

Triggers:

- `workflow_call`

Called by ingress:

- [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml), job `load-allowed-pr-authors`

Ingress runs this job only on `pull_request` events (`if: github.event_name == 'pull_request'`), so non-PR events skip this checkout step.

## API / Interface

`workflow_call` outputs:

| Output | Type | Meaning |
|--------|------|---------|
| `allowed_pr_authors_json` | JSON array string | Compact JSON array of allowed PR author logins, used by ingress `contains(fromJSON(...), github.event.pull_request.user.login)` checks |
| `allowed_pr_authors_csv` | string | Same logins as comma-separated values for workflows that accept CSV inputs |

## Configuration

Top-level permissions:

- `contents: read`

The job checks out **`elastic/oblt-aw`** at `main` with sparse checkout (`fetch-depth: 1`) and reads only:

- `config/obs/allowed_pr_authors.json`

It then emits outputs with:

- `jq -c .` for `allowed_pr_authors_json`
- `jq -r 'join(",")'` for `allowed_pr_authors_csv`

## References

- [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md)
- [config/obs/allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json)
