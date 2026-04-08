# Workflow: `gh-aw-automerge.yml`

## Overview

Source file: [.github/workflows/gh-aw-automerge.yml](../../.github/workflows/gh-aw-automerge.yml)

This workflow discovers qualifying bot-authored PRs, runs the GH-AW mention-in-pr approval step for each candidate PR, and enables squash auto-merge when gates are satisfied.

## Prerequisites

- Triggered via `workflow_call`.
- Requires qualifying PRs authored by `elastic-vault-github-plugin-prod[bot]` with label `oblt-aw/ai/merge-ready`.

## Usage

Jobs:

- `discover`: scans open PRs and outputs a JSON list of qualifying PR numbers.
- `approve`: matrix-invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` for each qualifying PR (Copilot approval gates).
- `enable-automerge`: verifies checks/reviews and enables GraphQL auto-merge (squash) for eligible PRs.

Eligibility checks include:

- not draft
- not from fork
- all check-runs completed with allowed conclusions (`success`, `skipped`, `neutral`)
- at least one `APPROVED` review from `github-actions[bot]`

## Configuration

Permissions:

- `actions: read`
- `checks: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- **Secrets:** `COPILOT_GITHUB_TOKEN` (required) — forwarded from the ingress caller for the GH-AW approval job.

## References

- Routing rules: [docs/routing/automerge-routing.md](../routing/automerge-routing.md)
