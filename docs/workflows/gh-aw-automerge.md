# Workflow: `gh-aw-automerge.yml`

## Overview

Source file: `.github/workflows/gh-aw-automerge.yml`

This workflow discovers qualifying bot-authored PRs, runs an approval sub-workflow, and enables squash auto-merge when gates are satisfied.

## Prerequisites

- Triggered via `workflow_call`.
- Requires qualifying PRs authored by `elastic-vault-github-plugin-prod[bot]` with label `oblt-aw/ai/merge-ready`.

## Usage

Jobs:

- `discover`: scans open PRs and outputs a JSON list of qualifying PR numbers.
- `approve`: matrix-calls `gh-aw-automerge-approve.yml` for each qualifying PR.
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

- no required inputs or secrets

## References

- Approver workflow: `docs/workflows/gh-aw-automerge-approve.md`
- Routing notes: `.github/workflow-routing/automerge/README.md`
