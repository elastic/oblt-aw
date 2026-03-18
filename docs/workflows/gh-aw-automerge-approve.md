# Workflow: `gh-aw-automerge-approve.yml`

## Overview

Source file: `.github/workflows/gh-aw-automerge-approve.yml`

This reusable sub-workflow evaluates a single pull request for automerge eligibility and approves it only when all required gates pass.

## Prerequisites

- Triggered via `workflow_call`.
- Required input: `pr-number` (string).

## Usage

The job `run` delegates to:

- `elastic/ai-github-actions/.github/workflows/gh-aw-mention-in-pr-by-id.lock.yml@v0`

Gate checks (as instructed by the prompt):

- author is `elastic-vault-github-plugin-prod[bot]`
- label `oblt-aw/ai/merge-ready` is present
- PR is not draft
- PR is not from a fork
- head ref differs from base ref
- all check-runs are complete and non-failing

Behavior:

- approve only when all gates are true
- do not approve and do not request changes otherwise

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

- Input: `pr-number` (`required: true`, `type: string`)

## References

- Parent workflow: `docs/workflows/gh-aw-automerge.md`
